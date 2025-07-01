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

        # ARP Flood (priority 1)
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