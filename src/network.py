from mininet.link import TCLink
from mininet.node import Host # Import Host for standard Mininet hosts
import subprocess
import os
import time
import requests

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

class ComplexTopo:
    """
    Defines a more complex SDN topology with multiple switches and standard hosts.
    This example uses a spine-leaf architecture.
    """
    def build(self, net, num_hosts, num_switches):
        # Ensure at least 2 switches for spine-leaf (one spine, one leaf)
        if num_switches < 2:
            num_switches = 2
            print("[WARNING] Complex topology requires at least 2 switches. Setting num_switches to 2.")

        spine_switches = []
        leaf_switches = []

        # Assuming num_switches is split into spine and leaf (e.g., half each)
        num_spine = max(1, num_switches // 2)
        num_leaf = max(1, num_switches - num_spine)

        # Spine Switches
        for i in range(1, num_spine + 1):
            switch = net.addSwitch(f"s_spine{i}")
            spine_switches.append(switch)

        # Leaf Switches
        for i in range(1, num_leaf + 1):
            switch = net.addSwitch(f"s_leaf{i}")
            leaf_switches.append(switch)

        # Standard Mininet hosts
        hosts = []
        for i in range(1, num_hosts + 1):
            host = net.addHost(f"h{i}")
            hosts.append(host)

        # Connect hosts to leaf switches
        for i, host in enumerate(hosts):
            # Distribute hosts among leaf switches
            net.addLink(host, leaf_switches[i % num_leaf], cls=TCLink, bw=50, delay="10ms")

        # Connect leaf switches to spine switches (full mesh between spine and leaf)
        for leaf_s in leaf_switches:
            for spine_s in spine_switches:
                net.addLink(leaf_s, spine_s, cls=TCLink, bw=100, delay="5ms")

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

def start_ryu_controller():
    """
    Starts the Ryu controller as a subprocess.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(script_dir, "controller.py")
    
    try:
        print("[INFO] Starting Ryu controller...")
        process = subprocess.Popen(
            ["ryu-manager", "--verbose", path, "ryu.app.rest_conf_switch", "ryu.app.ofctl_rest"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            preexec_fn=os.setsid
        )
        print("[INFO] Ryu controller started.")
        print("[INFO] Waiting for Ryu controller REST API to be ready...")

        # Wait for REST API to be up (max 20 seconds)
        for _ in range(20):
            try:
                resp = requests.get("http://localhost:8080/stats/switches", timeout=1)
                if resp.status_code == 200:
                    print("[INFO] Ryu REST API is up.")
                    return process
            except Exception:
                pass
            time.sleep(1)

        print("[ERROR] Ryu controller REST API did not become ready in time!")
        out, err = process.communicate(timeout=2)
        print("STDOUT:", out)
        print("STDERR:", err)
        return None
    except Exception as e:
        print(f"[ERROR] Failed to start Ryu controller: {e}")
        raise
