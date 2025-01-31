import os
import time
import tkinter as tk
from comnetsemu.net import Containernet, VNFManager
from mininet.node import RemoteController, OVSKernelSwitch
from mininet.log import setLogLevel, info
from mininet.link import TCLink
from gui import ServiceDeployGUI
from network import MyTopo, start_ryu_controller
from services import setup_docker_images, cleanup_containers, container_counter

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

        # Deploy "nginx" service called colab on all hosts
        for host in net.hosts:
            if host.name not in container_counter:
                container_counter[host.name] = {}
            if "colab" not in container_counter[host.name]:
                container_counter[host.name]["colab"] = 0
            while container_counter[host.name]["colab"] < 2:
                container_counter[host.name]["colab"] += 1
                colab_container_name = f"colab_{host.name}_{container_counter[host.name]['colab']}"
                mgr.addContainer(colab_container_name, host.name, "nginx:alpine", "nginx", docker_args={})
                print(f"[INFO] Colab service started on {host.name}")

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
