from mininet.net import Mininet
from mininet.node import RemoteController, OVSKernelSwitch
from mininet.log import setLogLevel, info
from mininet.link import TCLink
from mininet.cli import CLI
from gui import ServiceDeployGUI
from services import ServiceManager
import threading
import tkinter as tk
import os
import time

class MyTopo:
    """
    Defines a simple SDN topology with multiple switches and standard hosts.
    Each host is connected to a switch, and switches are connected in a ring.
    """
    def build(self, net, num_hosts, num_switches):
        # Switches
        switches = []
        for i in range(1, num_switches + 1):
            switch = net.addSwitch(f"s{i}")
            switches.append(switch)
            
        for i in range(1, num_hosts + 1):
            net.addHost(f"h{i}") 

        # Links
        # Connect each host to a switch in a round-robin manner
        for i in range(1, num_hosts + 1):
            host = net.get(f"h{i}") 
            # Connect the host to a switch, using TCLink for bandwidth and delay
            net.addLink(host, switches[(i - 1) % num_switches], cls=TCLink, bw=50, delay="10ms")

        # Connect each switch to the next switch in a circular manner (ring topology)
        for i in range(num_switches):
            net.addLink(switches[i], switches[(i + 1) % num_switches], cls=TCLink, bw=100, delay="5ms")

# class ComplexTopo:
#     """
#     Defines a more complex SDN topology with multiple switches and standard hosts.
#     This example uses a spine-leaf architecture.
#     """
#     def build(self, net, num_hosts, num_switches):
#         # Ensure at least 2 switches for spine-leaf (one spine, one leaf)
#         if num_switches < 2:
#             num_switches = 2
#             print("[WARNING] Complex topology requires at least 2 switches. Setting num_switches to 2.")

#         spine_switches = []
#         leaf_switches = []

#         # Assuming num_switches is split into spine and leaf (e.g., half each)
#         num_spine = max(1, num_switches // 2)
#         num_leaf = max(1, num_switches - num_spine)

#         # Spine Switches
#         for i in range(1, num_spine + 1):
#             switch = net.addSwitch(f"s_spine{i}")
#             spine_switches.append(switch)

#         # Leaf Switches
#         for i in range(1, num_leaf + 1):
#             switch = net.addSwitch(f"s_leaf{i}")
#             leaf_switches.append(switch)

#         # Standard Mininet hosts
#         hosts = []
#         for i in range(1, num_hosts + 1):
#             host = net.addHost(f"h{i}")
#             hosts.append(host)

#         # Connect hosts to leaf switches
#         for i, host in enumerate(hosts):
#             # Distribute hosts among leaf switches
#             net.addLink(host, leaf_switches[i % num_leaf], cls=TCLink, bw=50, delay="10ms")

#         # Connect leaf switches to spine switches (full mesh between spine and leaf)
#         for leaf_s in leaf_switches:
#             for spine_s in spine_switches:
#                 net.addLink(leaf_s, spine_s, cls=TCLink, bw=100, delay="5ms")

class ComplexTopo:
    """
    Defines a more complex SDN topology with multiple switches and standard hosts.
    This example uses a spine-leaf architecture.
    """
    def build(self, net, num_hosts, num_switches):
        if num_switches < 2:
            num_switches = 2
            print("[WARNING] Complex topology requires at least 2 switches. Setting num_switches to 2.")

        num_spine = max(1, num_switches // 2)
        num_leaf = max(1, num_switches - num_spine)

        # Add spine and leaf switches
        spine_switches = [net.addSwitch(f"s_spine{i+1}") for i in range(num_spine)]
        leaf_switches = [net.addSwitch(f"s_leaf{i+1}") for i in range(num_leaf)]

        # Add hosts and connect each to a leaf switch (round-robin)
        for i in range(num_hosts):
            host = net.addHost(f"h{i+1}")
            net.addLink(host, leaf_switches[i % num_leaf], cls=TCLink, bw=50, delay="10ms")

        # Connect each leaf switch to all spine switches (full mesh)
        for leaf in leaf_switches:
            for spine in spine_switches:
                net.addLink(leaf, spine, cls=TCLink, bw=100, delay="5ms")

def build_topology(topology_type, net):
    """
    Builds the selected network topology.

    Args:
        topology_type: A string indicating the topology type ("simple" or "complex").
        net: The Mininet network object to build the topology on.
    """
    if topology_type == "simple":
        topo = MyTopo()
        topo.build(net, num_hosts=6, num_switches=4) 
    elif topology_type == "complex":
        topo = ComplexTopo()
        topo.build(net, num_hosts=8, num_switches=6) 
    else:
        raise ValueError(f"Unknown topology type: {topology_type}")


class NetworkManager:
    """
    Manages the Mininet network, Ryu controller, and service deployment GUI.
    """
    def __init__(self, topology_type):
        self.topology_type = topology_type
        self.net = None
        self.service_manager = ServiceManager()
        self.flow_modification_queue = self.service_manager.get_flow_queue()

    def start_network(self):
        """
        Starts the Mininet network and Ryu controller.
        """
        setLogLevel("info")
        self.service_manager.clean_shared_folder() 

        try:
            time.sleep(5)
            # Initialize Mininet with a remote controller and OVS switches
            controller = RemoteController("c1", ip="127.0.0.1", port=6653)
            self.net = Mininet(switch=OVSKernelSwitch, link=TCLink, build=False)
            
            info("[INFO] Building network topology...\n")
            build_topology(self.topology_type, self.net)
            self.net.addController(controller) 

            info("[INFO] Starting the network...\n")
            self.net.start()
            time.sleep(20)
            info("[INFO] Network started...\n")
            self._configure_hosts()
            info("[INFO] Starting GUI...\n")
            self.start_gui()
            
            # while threading.active_count() > 1:
            #     time.sleep(1)

            info("[INFO] Starting Mininet CLI...\n")
            CLI(self.net)
            info("[INFO] Mininet CLI stopped...\n")
            
        except Exception as e:
            print(f"[ERROR] An error occurred: {e}")
        finally:
            self.stop_network() 

    def _configure_hosts(self):
        """
        Configures IP addresses for hosts and ensures necessary scripts are accessible.
        """
        for i, host in enumerate(self.net.hosts):
            # Assign IPs based on their order, starting from 10.0.0.1
            host.setIP(f"10.0.0.{i+1}") 
            info(f"[INFO] Configured host {host.name} with IP {host.IP()}\n")
            
            # Ensure the /shared/scripts directory exists on each host
            host.cmd("mkdir -p /shared/scripts") 

            # Copy application scripts to each host's /shared/scripts directory
            # This ensures they can be executed by host.cmd() later
            script_dir = os.path.join(os.path.dirname(__file__), "scripts")
            if not os.path.exists(script_dir):
                print(f"[WARNING] Script directory not found at {script_dir}. Services might fail to deploy.")
                # Create a dummy script directory if it doesn't exist to prevent errors
                os.makedirs(script_dir, exist_ok=True)
            
            for script_file in os.listdir(script_dir):
                if script_file.endswith(".py"):
                    src_path = os.path.join(script_dir, script_file)
                    dst_path = os.path.join("/shared/scripts", script_file)
                    # Use 'cp' command on the host to copy the script
                    host.cmd(f"cp {src_path} {dst_path}") 
                    info(f"[INFO] Copied {script_file} to {host.name}:{dst_path}\n")

    def start_gui(self):
        """
        Starts the GUI in a separate thread to avoid blocking the main thread.
        """
        def gui_thread():
            root = tk.Tk()
            # Pass the network object and the flow modification queue to the GUI
            ServiceDeployGUI(root, self.net, self.flow_modification_queue) 
            info("[INFO] GUI started...\n")
            root.mainloop()
        
        threading.Thread(target=gui_thread, daemon=True).start()

    def stop_network(self):
        """
        Stops the Mininet network and cleans up resources.
        """
        print("[INFO] Stopping the network...")
        if self.net:
            self.net.stop() 
        print("[INFO] Stopping the manager...")
        os.system("sudo mn -c") 

        print("[INFO] Cleaning up the /shared folder...")
        self.service_manager.clean_shared_folder() 
