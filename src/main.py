import os
import time
import tkinter as tk
from comnetsemu.net import Containernet, VNFManager
from mininet.node import RemoteController, OVSKernelSwitch
from mininet.log import setLogLevel, info
from mininet.link import TCLink
from gui import ServiceDeployGUI
from network import build_topology, start_ryu_controller
from services import deploy_colab_service, setup_docker_images, cleanup_containers, clean_shared_folder

def start(topology_type):
    setLogLevel("info")
    cleanup_containers()
    setup_docker_images()
    ryu_process = start_ryu_controller()

    try:
        time.sleep(5)
        controller = RemoteController("c1", ip="127.0.0.1", port=6633)
        net = Containernet(controller=controller, switch=OVSKernelSwitch, link=TCLink, build=False)
        mgr = VNFManager(net)
        
        # Build the desired topology
        build_topology(topology_type, net)
        
        net.addController(controller)

        print("[INFO] Starting the network...")
        net.start()
        info("[INFO] Network started...\n")

        # Deploy "colab" service on all hosts
        deploy_colab_service(mgr)

        info("[INFO] Starting GUI...\n")
        root = tk.Tk()
        ServiceDeployGUI(root, mgr, net)
        info("[INFO] GUI started...\n")
        root.mainloop()

    except Exception as e:
        print(f"[ERROR] An error occurred: {e}")
    finally:
        print("[INFO] Stopping the network...")
        net.stop()
        print("[INFO] Stopping the manager...")
        mgr.stop()
        os.system("sudo mn -c")

        print("[INFO] Cleaning up the /shared folder...")
        clean_shared_folder()

        print("[INFO] Stopping the Ryu controller...")
        if ryu_process:
            ryu_process.terminate()

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

    start(topology_type)
