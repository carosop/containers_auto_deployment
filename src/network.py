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
    Each host is connected to a switch and switches are connected in a ring.
    """
    def build(self, net, num_hosts, num_switches, bw_h, bw_s, link_type="ring"):
        switches = []
        for i in range(1, num_switches + 1):
            switches.append(net.addSwitch(f"s{i}"))

        for i in range(1, num_hosts + 1):
            net.addHost(f"h{i}")

        for i in range(1, num_hosts + 1):
            host = net.get(f"h{i}")
            net.addLink(host, switches[(i - 1) % num_switches], cls=TCLink, bw=bw_h, delay="10ms")

        if link_type == "ring":
            for i in range(num_switches):
                net.addLink(switches[i], switches[(i + 1) % num_switches], cls=TCLink, bw=bw_s, delay="5ms")
        elif link_type == "linear":
            for i in range(num_switches - 1):
                net.addLink(switches[i], switches[i + 1], cls=TCLink, bw=bw_s, delay="5ms")
        else:
            raise ValueError("Invalid link_type: choose 'ring' or 'linear'")


def build_topology(topology_type, net, link_type="ring"):
    topo = MyTopo()
    if topology_type == "simple":
        topo.build(net, num_hosts=6, num_switches=4, bw_h=50, bw_s=100, link_type=link_type)
    elif topology_type == "complex":
        topo.build(net, num_hosts=19, num_switches=7, bw_h=100, bw_s=150, link_type=link_type)
    else:
        raise ValueError(f"Unknown topology type: {topology_type}")


class NetworkManager:
    """
    Manages the Mininet network, Ryu controller and service deployment GUI.
    """
    def __init__(self, topology_type, link_type="ring"):
        self.topology_type = topology_type
        self.link_type = link_type
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
            build_topology(self.topology_type, self.net, link_type=self.link_type)
            self.net.addController(controller) 

            info("[INFO] Starting the network...\n")
            self.net.start()
            time.sleep(20)
            info("[INFO] Network started...\n")
            self._configure_hosts()
            info("[INFO] Starting GUI...\n")
            self.start_gui()

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
            # to use host.cmd() later
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
