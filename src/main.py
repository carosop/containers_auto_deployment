import os
import time
import tkinter as tk
from mininet.net import Mininet
from mininet.node import RemoteController, OVSKernelSwitch
from mininet.log import setLogLevel, info
from mininet.link import TCLink
from gui import ServiceDeployGUI
from network import build_topology, start_ryu_controller
from services import ServiceManager
from mininet.cli import CLI
import threading

class NetworkManager:
    """
    Manages the Mininet network, Ryu controller, and service deployment GUI.
    """
    def __init__(self, topology_type):
        self.topology_type = topology_type
        self.net = None
        # self.ryu_process = start_ryu_controller()
        self.service_manager = ServiceManager()
        self.flow_modification_queue = self.service_manager.get_flow_queue()

    def start_network(self):
        """
        Starts the Mininet network and Ryu controller.
        """
        setLogLevel("info")
        # Cleanup any previous Mininet state
        os.system("sudo mn -c") 
        self.service_manager.clean_shared_folder() 

        try:
            time.sleep(5)  # Give Ryu controller time to start
            # Initialize Mininet with a remote controller and OVS switches
            controller = RemoteController("c1", ip="127.0.0.1", port=6653)
            self.net = Mininet(switch=OVSKernelSwitch, link=TCLink, build=False)
            
            info("[INFO] Building network topology...\n")
            build_topology(self.topology_type, self.net)
            self.net.addController(controller) 

            info("[INFO] Starting the network...\n")
            self.net.start()
            
            info("[INFO] Network started...\n")

            # # Wait for all switches to connect to the controller
            # expected_switches = len(self.net.switches)
            # for _ in range(20):
            #     try:
            #         import requests
            #         resp = requests.get("http://localhost:8080/stats/switches", timeout=1)
            #         if resp.status_code == 200:
            #             switches = resp.json()
            #             if len(switches) >= expected_switches:
            #                 info(f"[INFO] All {expected_switches} switches connected to Ryu controller.\n")
            #                 break
            #     except Exception:
            #         pass
            #     time.sleep(1)
            # else:
            #     print("[WARNING] Not all switches connected to Ryu controller in time.")
            
            # Configure host IPs and ensure scripts are accessible
            self._configure_hosts()
            time.sleep(20)
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

        print("[INFO] Stopping the Ryu controller...")
        if hasattr(self, "ryu_process") and self.ryu_process is not None:
            self.ryu_process.terminate()
            print("[INFO] Ryu controller stopped.")


if __name__ == "__main__":
    print("Select the topology type:")
    print("1. Simple")
    print("2. Complex")
    choice = input("Enter the number of your choice: ")

    if choice == "1":
        topology_type = "simple"
    elif choice == "2":
        topology_type = "complex"
    else:
        print("[ERROR] Invalid choice. Exiting.")
        exit(1)

    network_manager = NetworkManager(topology_type)
    network_manager.start_network()