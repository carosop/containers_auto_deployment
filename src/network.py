import subprocess
from mininet.link import TCLink

class MyTopo:
    def build(self, net):
        """
        Define the SDN topology with multiple switches and hosts.
        """
        # Switches
        s1 = net.addSwitch("s1", protocols="OpenFlow13", stp=True)
        s2 = net.addSwitch("s2", protocols="OpenFlow13", stp=True)
        s3 = net.addSwitch("s3", protocols="OpenFlow13", stp=True)
        s4 = net.addSwitch("s4", protocols="OpenFlow13", stp=True)

        # Docker hosts
        h1 = net.addDockerHost("h1", ip="10.0.0.1", dimage="auto_deployment", docker_args={"hostname": "h1"})
        h2 = net.addDockerHost("h2", ip="10.0.0.2", dimage="auto_deployment", docker_args={"hostname": "h2"})
        h3 = net.addDockerHost("h3", ip="10.0.0.3", dimage="auto_deployment", docker_args={"hostname": "h3"})
        h4 = net.addDockerHost("h4", ip="10.0.0.4", dimage="auto_deployment", docker_args={"hostname": "h4"})
        h5 = net.addDockerHost("h5", ip="10.0.0.5", dimage="auto_deployment", docker_args={"hostname": "h5"})
        h6 = net.addDockerHost("h6", ip="10.0.0.6", dimage="auto_deployment", docker_args={"hostname": "h6"})
        # h1 = net.addDockerHost("h1", ip="10.0.0.1", dimage="dev_test", docker_args={"hostname": "h1"})
        # h2 = net.addDockerHost("h2", ip="10.0.0.2", dimage="dev_test", docker_args={"hostname": "h2"})
        # h3 = net.addDockerHost("h3", ip="10.0.0.3", dimage="dev_test", docker_args={"hostname": "h3"})
        # h4 = net.addDockerHost("h4", ip="10.0.0.4", dimage="dev_test", docker_args={"hostname": "h4"})
        # h5 = net.addDockerHost("h5", ip="10.0.0.5", dimage="dev_test", docker_args={"hostname": "h5"})
        # h6 = net.addDockerHost("h6", ip="10.0.0.6", dimage="dev_test", docker_args={"hostname": "h6"})
        
        # Links
        net.addLink(h1, s1, cls=TCLink, bw=50, delay="10ms")
        net.addLink(h2, s2, cls=TCLink, bw=50, delay="10ms")
        net.addLink(h3, s2, cls=TCLink, bw=50, delay="10ms")
        net.addLink(h4, s3, cls=TCLink, bw=50, delay="10ms")
        net.addLink(h5, s4, cls=TCLink, bw=50, delay="10ms")
        net.addLink(h6, s4, cls=TCLink, bw=50, delay="10ms")
        net.addLink(s4, s1, cls=TCLink, bw=100, delay="5ms")
        net.addLink(s1, s2, cls=TCLink, bw=100, delay="5ms")
        net.addLink(s2, s3, cls=TCLink, bw=100, delay="5ms")
        net.addLink(s3, s4, cls=TCLink, bw=100, delay="5ms")   

class ComplexTopo:
    def build(self, net):
        """
        Define a more complex SDN topology.
        """
        # Switches
        s1 = net.addSwitch("s1", protocols="OpenFlow13", stp=True)
        s2 = net.addSwitch("s2", protocols="OpenFlow13", stp=True)
        s3 = net.addSwitch("s3", protocols="OpenFlow13", stp=True)
        s4 = net.addSwitch("s4", protocols="OpenFlow13", stp=True)
        s5 = net.addSwitch("s5", protocols="OpenFlow13", stp=True)
        s6 = net.addSwitch("s6", protocols="OpenFlow13", stp=True)

        # Docker hosts
        h1 = net.addDockerHost("h1", ip="10.0.0.1", dimage="auto_deployment", docker_args={"hostname": "h1"})
        h2 = net.addDockerHost("h2", ip="10.0.0.2", dimage="auto_deployment", docker_args={"hostname": "h2"})
        h3 = net.addDockerHost("h3", ip="10.0.0.3", dimage="auto_deployment", docker_args={"hostname": "h3"})
        h4 = net.addDockerHost("h4", ip="10.0.0.4", dimage="auto_deployment", docker_args={"hostname": "h4"})
        h5 = net.addDockerHost("h5", ip="10.0.0.5", dimage="auto_deployment", docker_args={"hostname": "h5"})
        h6 = net.addDockerHost("h6", ip="10.0.0.6", dimage="auto_deployment", docker_args={"hostname": "h6"})
        h7 = net.addDockerHost("h7", ip="10.0.0.7", dimage="auto_deployment", docker_args={"hostname": "h7"})
        h8 = net.addDockerHost("h8", ip="10.0.0.8", dimage="auto_deployment", docker_args={"hostname": "h8"})
        
        # Links
        net.addLink(h1, s1, cls=TCLink, bw=50, delay="10ms")
        net.addLink(h2, s2, cls=TCLink, bw=50, delay="10ms")
        net.addLink(h3, s3, cls=TCLink, bw=50, delay="10ms")
        net.addLink(h4, s4, cls=TCLink, bw=50, delay="10ms")
        net.addLink(h5, s5, cls=TCLink, bw=50, delay="10ms")
        net.addLink(h6, s6, cls=TCLink, bw=50, delay="10ms")
        net.addLink(h7, s1, cls=TCLink, bw=50, delay="10ms")
        net.addLink(h8, s2, cls=TCLink, bw=50, delay="10ms")
        net.addLink(s1, s2, cls=TCLink, bw=100, delay="5ms")
        net.addLink(s2, s3, cls=TCLink, bw=100, delay="5ms")
        net.addLink(s3, s4, cls=TCLink, bw=100, delay="5ms")
        net.addLink(s4, s5, cls=TCLink, bw=100, delay="5ms")
        net.addLink(s5, s6, cls=TCLink, bw=100, delay="5ms")
        net.addLink(s6, s1, cls=TCLink, bw=100, delay="5ms")
        net.addLink(s1, s3, cls=TCLink, bw=100, delay="5ms")
        net.addLink(s2, s4, cls=TCLink, bw=100, delay="5ms")
        net.addLink(s3, s5, cls=TCLink, bw=100, delay="5ms")
        net.addLink(s4, s6, cls=TCLink, bw=100, delay="5ms")


def build_topology(topology_type, net):
    """
    Build the desired topology
    """
    if topology_type == "simple":
        topo = MyTopo()
    elif topology_type == "complex":
        topo = ComplexTopo()
    else:
        raise ValueError(f"Unknown topology type: {topology_type}")
    
    topo.build(net)

def start_ryu_controller():
    """
    Start the Ryu controller.
    """
    try:
        print("[INFO] Starting Ryu controller...")
        process = subprocess.Popen(
            ["ryu-manager", "/usr/lib/python3/dist-packages/ryu/app/simple_switch_stp_13.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        print("[INFO] Ryu controller started.")
        return process
    except Exception as e:
        print(f"[ERROR] Failed to start Ryu controller: {e}")
        raise