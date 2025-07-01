import networkx
from mininet.node import OVSKernelSwitch
import requests 
import json 

class FlowManager:
    def __init__(self, ryu_api_url='http://localhost:8080'): # Add Ryu API URL
        self.active_flows = {}
        self.ryu_api_url = ryu_api_url # Store the API URL

    def get_switch_for_host(self, net, host_name):
        host = net.get(host_name)
        for link in net.links:
            if link.intf1.node == host and isinstance(link.intf2.node, OVSKernelSwitch):
                return link.intf2.node
            elif link.intf2.node == host and isinstance(link.intf1.node, OVSKernelSwitch):
                return link.intf1.node
        return None

    def get_port(self, net, node1, node2):
        for link in net.links:
            if link.intf1.node == node1 and link.intf2.node == node2:
                return node1.ports[link.intf1]
            elif link.intf2.node == node1 and link.intf1.node == node2:
                return node1.ports[link.intf2]
        return None

    def get_path(self, net, src, dst):
        g = networkx.Graph()
        for link in net.links:
            n1, n2 = link.intf1.node, link.intf2.node
            if isinstance(n1, OVSKernelSwitch) and isinstance(n2, OVSKernelSwitch):
                g.add_edge(n1.name, n2.name)
        try:
            return networkx.shortest_path(g, src, dst)
        except Exception:
            return None

    def _send_flow_to_ryu(self, flow_data):
        dpid = flow_data['dpid']
        flow_action = flow_data['action']  # 'add' o 'remove'
        dpid_int = int(dpid, 16) if isinstance(dpid, str) else dpid

        url = f"{self.ryu_api_url}/stats/flowentry/{flow_action}"  # cmd endpoint
        
        match = {
            "eth_type": 0x0800,
            "ipv4_src": flow_data['src_ip'],
            "ipv4_dst": flow_data['dst_ip'],
            "in_port": flow_data['in_port']
        }
        if flow_data['protocol'] == 6:  # TCP
            match["ip_proto"] = 6
            if flow_data['src_port']:
                match["tcp_src"] = flow_data['src_port']
            if flow_data['dst_port']:
                match["tcp_dst"] = flow_data['dst_port']
        elif flow_data['protocol'] == 1:  # ICMP
            match["ip_proto"] = 1

        actions = [{"type": "OUTPUT", "port": flow_data['out_port']}]

        flow_entry = {
            "dpid": dpid_int,
            "cookie": 0,
            "cookie_mask": 0,
            "table_id": 0,
            "idle_timeout": 0,
            "hard_timeout": 0,
            "priority": flow_data['priority'],
            "flags": 0,
            "match": match,
            "actions": actions
        }

        if flow_action == 'remove':
            flow_entry.pop("cookie")
            flow_entry.pop("cookie_mask")
        
        headers = {'Content-Type': 'application/json'}
        try:
            response = requests.post(url, data=json.dumps(flow_entry), headers=headers)
            response.raise_for_status()
            print(f"[Ryu API] Flow {flow_action}ed for DPID {dpid_int}: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Failed to {flow_action} flow via Ryu API for DPID {dpid_int}: {e}")

    def add_flow_queue(self, net, service_key, src_host, dst_host, protocol, src_port=None, dst_port=None):
        # The flow_queue concept will be less critical if you're directly pushing to Ryu,
        # but you can still use it for logging or for batching if needed.
        # For direct API interaction, we'll send immediately.
        
        src_ip, dst_ip = src_host.IP(), dst_host.IP()
        sw1, sw2 = self.get_switch_for_host(net, src_host.name), self.get_switch_for_host(net, dst_host.name)
        in_port = self.get_port(net, sw1, src_host)
        out_port = self.get_port(net, sw2, dst_host)
        
        if sw1.name == sw2.name:
            flow_params = {
                'action': 'add', 'dpid': sw1.dpid, 'src_ip': src_ip, 'dst_ip': dst_ip,
                'protocol': protocol, 'src_port': src_port, 'dst_port': dst_port,
                'in_port': in_port, 'out_port': out_port, 'priority': 200, 'service_key': service_key
            }
            self._send_flow_to_ryu(flow_params)
            self.active_flows[(service_key, src_ip, dst_ip, dst_port, protocol, sw1.dpid, in_port)] = flow_params
            
            # Reverse flow
            rev_flow_params = flow_params.copy()
            rev_flow_params.update({'src_ip': dst_ip, 'dst_ip': src_ip, 'src_port': dst_port, 'dst_port': src_port,
                                    'in_port': out_port, 'out_port': in_port})
            self._send_flow_to_ryu(rev_flow_params)
            self.active_flows[(service_key, dst_ip, src_ip, src_port, protocol, sw1.dpid, out_port)] = rev_flow_params
            return

        path = self.get_path(net, sw1.name, sw2.name)
        for i, sw_name in enumerate(path):
            sw = net.get(sw_name)
            dpid = sw.dpid
            if i == 0:
                in_p = in_port
                out_p = self.get_port(net, sw, net.get(path[i+1]))
            elif i == len(path) - 1:
                in_p = self.get_port(net, sw, net.get(path[i-1]))
                out_p = out_port
            else:
                in_p = self.get_port(net, sw, net.get(path[i-1]))
                out_p = self.get_port(net, sw, net.get(path[i+1]))
            
            flow_params = {
                'action': 'add', 'dpid': dpid, 'src_ip': src_ip, 'dst_ip': dst_ip,
                'protocol': protocol, 'src_port': src_port, 'dst_port': dst_port,
                'in_port': in_p, 'out_port': out_p, 'priority': 100, 'service_key': service_key
            }
            self._send_flow_to_ryu(flow_params)
            self.active_flows[(service_key, src_ip, dst_ip, dst_port, protocol, dpid, in_p)] = flow_params
            
            # Reverse flow
            rev_flow_params = flow_params.copy()
            rev_flow_params.update({'src_ip': dst_ip, 'dst_ip': src_ip, 'src_port': dst_port, 'dst_port': src_port,
                                    'in_port': out_p, 'out_port': in_p})
            self._send_flow_to_ryu(rev_flow_params)
            self.active_flows[(service_key, dst_ip, src_ip, src_port, protocol, dpid, out_p)] = rev_flow_params

    def remove_flow_queue(self, service_key, src_ip, dst_ip, protocol=None, src_port=None, dst_port=None):
        keys = [k for k in self.active_flows if k[0] == service_key and k[1] == src_ip and k[2] == dst_ip and
                (protocol is None or k[4] == protocol) and (dst_port is None or k[3] == dst_port)]
        for k in keys:
            flow = self.active_flows[k]
            flow_data = flow.copy()
            flow_data['action'] = 'delete'
            self._send_flow_to_ryu(flow_data) # Send removal request
            del self.active_flows[k]

    def get_active_flows(self):
        return self.active_flows