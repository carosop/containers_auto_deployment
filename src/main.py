import os
import time
import tkinter as tk
from comnetsemu.net import Containernet, VNFManager
from mininet.node import RemoteController, OVSKernelSwitch
from mininet.log import setLogLevel, info
from mininet.link import TCLink
from gui import ServiceDeployGUI
from network import MyTopo, start_ryu_controller
from services import deploy_colab_service, setup_docker_images, cleanup_containers

def start():
    setLogLevel("info")
    cleanup_containers()
    setup_docker_images()
    ryu_process = start_ryu_controller()

    try:
        time.sleep(5)
        controller = RemoteController("c1", ip="127.0.0.1", port=6633)
        net = Containernet(controller=controller, switch=OVSKernelSwitch, link=TCLink, build=False)
        mgr = VNFManager(net)
        topo = MyTopo()
        topo.build(net)
        net.addController(controller)

        print("[INFO] Starting the network...")
        net.start()
        info("[INFO] Network started...\n")

        # Deploy "colab" service on all hosts
        deploy_colab_service(mgr, net)

        info("[INFO] Starting GUI...\n")
        root = tk.Tk()
        ServiceDeployGUI(root, mgr, net)
        info("[INFO] GUI started...\n")
        root.mainloop()

    finally:
        print("[INFO] Stopping the network...")
        net.stop()
        print("[INFO] Stopping the manager...")
        mgr.stop()
        os.system("sudo mn -c")

        print("[INFO] Stopping the Ryu controller...")
        if ryu_process:
            ryu_process.terminate()

if __name__ == "__main__":
    start()
