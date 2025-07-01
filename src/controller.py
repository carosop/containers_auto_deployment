# from ryu.base import app_manager
# from ryu.controller import ofp_event
# from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
# from ryu.ofproto import ofproto_v1_3
# from ryu.lib.packet import packet, ethernet, ether_types, ipv4
# import threading

# class Controller(app_manager.RyuApp):
#     """
#     Simplified Ryu controller for OpenFlow 1.3 switches.
#     Installs flows based on requests from a shared queue.
#     """
#     OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

#     def __init__(self, *args, **kwargs):
#         super(Controller, self).__init__(*args, **kwargs)
#         print("[RYU] >>>>>>>>> My custom controller is running! <<<<<<<<<")
#         self.datapaths = {}
#         self.service_members = {}  # {service_key: [ip1, ip2, ...]}
#         self.lock = threading.Lock()

#     def update_service_members(self, service_members):
#         with self.lock:
#             self.service_members = service_members.copy()
#         self.logger.info(f"Updated service members: {self.service_members}")

#     @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
#     def switch_features_handler(self, ev):
#         print(f"[RYU] Switch connected: DPID={ev.msg.datapath.id}")
#         datapath = ev.msg.datapath
#         parser = datapath.ofproto_parser
#         ofproto = datapath.ofproto
#         self.datapaths[datapath.id] = datapath

#         # Table-miss flow: send unmatched packets to controller
#         match = parser.OFPMatch()
#         actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]
#         self.add_flow(datapath, 0, match, actions)

#         # Flood ARP packets
#         match_arp = parser.OFPMatch(eth_type=ether_types.ETH_TYPE_ARP)
#         actions_arp = [parser.OFPActionOutput(ofproto.OFPP_FLOOD)]
#         self.add_flow(datapath, 1, match_arp, actions_arp)

#     def add_flow(self, datapath, priority, match, actions):
#         parser = datapath.ofproto_parser
#         ofproto = datapath.ofproto
#         inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
#         mod = parser.OFPFlowMod(datapath=datapath, priority=priority, match=match, instructions=inst)
#         datapath.send_msg(mod)

#     @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
#     def _packet_in_handler(self, ev):
#         msg = ev.msg
#         datapath = msg.datapath
#         parser = datapath.ofproto_parser
#         ofproto = datapath.ofproto
#         in_port = msg.match['in_port']
#         pkt = packet.Packet(msg.data)
#         eth = pkt.get_protocol(ethernet.ethernet)
#         if eth.ethertype != ether_types.ETH_TYPE_IP:
#             return
#         ip_pkt = pkt.get_protocol(ipv4.ipv4)
#         src_ip = ip_pkt.src
#         dst_ip = ip_pkt.dst

#         # Check if src and dst are in the same service
#         allowed = False
#         with self.lock:
#             for members in self.service_members.values():
#                 if src_ip in members and dst_ip in members:
#                     allowed = True
#                     break

#         if not allowed:
#             self.logger.info(f"Blocked: {src_ip} -> {dst_ip} (not in same service)")
#             return

#         # Find output port for dst_ip
#         out_port = self._find_out_port(datapath, dst_ip)
#         if out_port is None:
#             self.logger.info(f"No out_port found for {dst_ip}")
#             return

#         # Install flow for this communication
#         match = parser.OFPMatch(
#             eth_type=ether_types.ETH_TYPE_IP,
#             ipv4_src=src_ip,
#             ipv4_dst=dst_ip,
#             in_port=in_port
#         )
#         actions = [parser.OFPActionOutput(out_port)]
#         self.add_flow(datapath, 100, match, actions)

#         # Forward the current packet
#         out = parser.OFPPacketOut(
#             datapath=datapath, buffer_id=ofproto.OFP_NO_BUFFER,
#             in_port=in_port, actions=actions, data=msg.data
#         )
#         datapath.send_msg(out)

#     def _find_out_port(self, datapath, dst_ip):
#         # For a simple topology, you can use ARP or static mapping.
#         # For now, flood if unknown.
#         return ofproto_v1_3.OFPP_FLOOD

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ether_types, ipv4
import threading

class Controller(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(Controller, self).__init__(*args, **kwargs)
        self.datapaths = {}
        self.lock = threading.Lock()
        print("[RYU] Custom controller is running")


    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto
        self.datapaths[datapath.id] = datapath

        # Default table-miss flow (priority 0 to send to controller)
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)

        # ARP Flood (priority 1) - keep this for network discovery
        match_arp = parser.OFPMatch(eth_type=ether_types.ETH_TYPE_ARP)
        actions_arp = [parser.OFPActionOutput(ofproto.OFPP_FLOOD)]
        self.add_flow(datapath, 1, match_arp, actions_arp)

    def add_flow(self, datapath, priority, match, actions, idle_timeout=0, hard_timeout=0): # Set idle/hard timeout to 0 for persistent flows
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(
            datapath=datapath, priority=priority, match=match,
            instructions=inst, idle_timeout=idle_timeout, hard_timeout=hard_timeout
        )
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        
        if eth.ethertype == ether_types.ETH_TYPE_ARP:
            return

        # If it's not an IP packet we're interested in, drop it or flood if needed
        if eth.ethertype != ether_types.ETH_TYPE_IP:
            # Potentially drop or flood non-IP traffic if not explicitly handled
            # For now, just drop unrecognized traffic to avoid excessive PacketIns
            # actions = []
            # out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id, in_port=in_port, actions=actions, data=msg.data)
            # datapath.send_msg(out)
            return

        ip_pkt = pkt.get_protocol(ipv4.ipv4)
        src_ip = ip_pkt.src
        dst_ip = ip_pkt.dst

        self.logger.warning(f"[WARNING] Packet-in for unhandled IP traffic: {src_ip} -> {dst_ip} on DPID {datapath.id}, in_port {in_port}")
        
        # Since flows are installed proactively by FlowManager,
        # any IP packet reaching here means there's no specific flow for it.
        # You can decide how to handle this:
        # 1. Drop the packet (default for unhandled traffic)
        # 2. Flood it (if you want default connectivity but prefer explicit flows for services)
        # 3. Dynamically install a default "flood" flow (less ideal for controlled SDN)
        
        # For now, we'll let the default table-miss handle it, which sends it back to the controller.
        # Since we've removed the reactive flow installation, these packets will continue
        # to hit the controller until a specific flow is installed by the FlowManager.
        # This serves as a debugging point: if a service flow isn't working, you'll see
        # these warnings.
        
        # To avoid continuous PacketIn for the same flow, you might consider installing
        # a drop flow for such unhandled packets or a temporary flood, but for a
        # proactive system, the goal is to *not* have these packets reach here.
        
        # If you still want a "default allowed" flow for unhandled IP traffic within
        # the same service *after* the proactive flows, you'd need the service_members
        # here, but the core idea is to rely on proactive installation.