import docker
import random
import subprocess

# Track flows between services
flows = {}
container_counter = {}

def setup_docker_images():
    """
    Prepare required Docker images. Pull missing images.
    """
    client = docker.from_env()
    images = [
        "httpd:alpine", "mysql:latest", "redis:latest", "prom/prometheus:latest",
        "grafana/grafana:latest", "elasticsearch:7.10.1", "kibana:7.10.1",
        "rabbitmq:latest", "bitnami/spark:latest", "nginx:alpine"
    ]
    for image in images:
        try:
            print(f"[INFO] Checking if image '{image}' is available locally...")
            if not client.images.list(name=image):
                print(f"[INFO] Image '{image}' not found locally. Pulling...")
                client.images.pull(image)
            else:
                print(f"[INFO] Image '{image}' already exists locally.")
        except docker.errors.DockerException as e:
            print(f"[ERROR] Failed to check or pull image {image}: {e}")

def deploy_service(mgr, service_name, net):
    """
    Deploys a service, choosing hosts automatically.
    """
    service_definitions = {
        "web": [("webserver", "httpd:alpine", "httpd-foreground"), 
                ("database", "mysql:latest", "mysqld")],
        "cache": [("redis", "redis:latest", "redis-server")],
        "monitoring": [("prometheus", "prom/prometheus:latest", "prometheus"), 
                       ("grafana", "grafana/grafana:latest", "grafana-server")],
        "logging": [("elasticsearch", "elasticsearch:7.10.1", "elasticsearch"), 
                    ("kibana", "kibana:7.10.1", "kibana")],
        "messaging": [("rabbitmq", "rabbitmq:latest", "rabbitmq-server")],
        "analytics": [("spark", "bitnami/spark:latest", "spark-shell")]
    }

    if service_name not in service_definitions:
        print(f"[ERROR] Service '{service_name}' not supported.")
        return

    required_hosts = len(service_definitions[service_name])
    available_hosts = [host.name for host in mgr.net.hosts if len(mgr.getContainersDhost(host.name)) < 2]

    # Ensure there are enough hosts by removing "colab" services if necessary
    if len(available_hosts) < required_hosts:
        for host in mgr.net.hosts:
            while len(mgr.getContainersDhost(host.name)) >= 2 and len(available_hosts) < required_hosts:
                colab_services = [s for s in mgr.getContainersDhost(host.name) if "colab" in s]
                if colab_services:
                    mgr.removeContainer(colab_services[0])
                    print(f"[INFO] Removed colab service: {colab_services[0]}")
                    available_hosts.append(host.name)
                else:
                    break

    if len(available_hosts) < required_hosts:
        print("[ERROR] Not enough available hosts even after removing colab services!")
        return

    selected_hosts = random.sample(available_hosts, required_hosts)

    for (app_name, image, command), host in zip(service_definitions[service_name], selected_hosts):
        if host not in container_counter:
            container_counter[host] = {}
        if app_name not in container_counter[host]:
            container_counter[host][app_name] = 0
        container_counter[host][app_name] += 1
        container_name = f"{app_name}_{host}_{container_counter[host][app_name]}"
        try:
            mgr.addContainer(container_name, host, image, command, docker_args={})
            print(f"[INFO] Service {app_name} started on {host}")
        except docker.errors.APIError as e:
            if e.status_code == 409:  # Conflict error
                print(f"[WARNING] Container name conflict for {container_name}. Removing existing container.")
                mgr.removeContainer(container_name)
                mgr.addContainer(container_name, host, image, command, docker_args={})
                print(f"[INFO] Service {app_name} started on {host}")

    setup_service_flows(mgr.net, service_definitions[service_name], selected_hosts)

    # Automatically set up communication flows between service components
    for i in range(len(service_definitions[service_name]) - 1):
        src_host = selected_hosts[i]
        dst_host = selected_hosts[i + 1]
        src_ip = net.get(src_host).IP()
        dst_ip = net.get(dst_host).IP()
        switch = get_switch_for_host(net, src_host)

        if switch:
            setup_flow(switch, src_ip, dst_ip, 1, 2)
            print(f"[INFO] Flow configured between {src_host} and {dst_host}")

    # Example communication test for "web" service
    if service_name == "web":
        test_service_communication(mgr.net, "webserver", "database")
    elif service_name == "monitoring":
        test_service_communication(mgr.net, "prometheus", "grafana")
    elif service_name == "logging":
        test_service_communication(mgr.net, "elasticsearch", "kibana")
    elif service_name == "messaging":
        test_service_communication(mgr.net, "rabbitmq", "rabbitmq")
    elif service_name == "analytics":
        test_service_communication(mgr.net, "spark", "spark")

def setup_service_flows(net, service_apps, hosts):
    """
    Configures SDN flows to enable communication between service components.
    """
    for i in range(len(service_apps) - 1):
        src_host = hosts[i]
        dst_host = hosts[i + 1]
        src_ip = net.get(src_host).IP()
        dst_ip = net.get(dst_host).IP()
        switch = get_switch_for_host(net, src_host)

        if switch:
            setup_flow(switch, src_ip, dst_ip, 1, 2)
            print(f"[INFO] Flow configured between {src_host} and {dst_host}")

def test_service_communication(net, client_service, server_service):
    """
    Tests communication between two services via a simulated HTTP request.
    """
    try:
        client_host = next((host for host in net.hosts if client_service in host.name), None)
        server_host = next((host for host in net.hosts if server_service in host.name), None)

        if not client_host or not server_host:
            print("[ERROR] Hosts not found for communication test.")
            return

        client_ip = net.get(client_host.name).IP()
        server_ip = net.get(server_host.name).IP()

        print(f"[INFO] Testing communication between {client_service} ({client_ip}) and {server_service} ({server_ip})...")

        response = subprocess.run(
            ["curl", f"http://{server_ip}"],
            capture_output=True,
            text=True
        )

        if response.returncode == 0:
            print(f"[SUCCESS] Communication successful! Output: {response.stdout}")
        else:
            print(f"[ERROR] Communication failed! Error: {response.stderr}")
    except Exception as e:
        print(f"[ERROR] Error in communication test: {e}")

def setup_flow(switch, src_ip, dst_ip, in_port, out_port):
    """
    Set up SDN flows.
    """
    flow_rule = f"priority=100,ip,nw_src={src_ip},nw_dst={dst_ip},actions=output:{out_port}"
    switch.dpctl('add-flow', flow_rule)
    flows[(src_ip, dst_ip)] = (switch, in_port, out_port)
    print(f"[INFO] Flow added: {src_ip} -> {dst_ip}")

def remove_flow(switch, src_ip, dst_ip):
    """
    Remove SDN flows.
    """
    flow_rule = f"priority=100,ip,nw_src={src_ip},nw_dst={dst_ip}"
    switch.dpctl('del-flows', flow_rule)
    if (src_ip, dst_ip) in flows:
        del flows[(src_ip, dst_ip)]
    print(f"[INFO] Flow removed: {src_ip} -> {dst_ip}")

def get_switch_for_host(net, host):
    """
    Finds the switch connected to a given host.
    """
    for link in net.links:
        if host in link.intf1.node.name:
            return link.intf2.node
        elif host in link.intf2.node.name:
            return link.intf1.node
    return None

def cleanup_containers():
    """
    Stop and remove Docker containers that begin with "webserver" or "database".
    """
    client = docker.from_env()
    try:
        containers = client.containers.list(all=True)
        for container in containers:
            if container.name.startswith("webserver") or container.name.startswith("database"):
                print(f"[INFO] Stopping and removing container: {container.name}")
                try:
                    container.stop()
                    container.remove()
                except docker.errors.NotFound:
                    print(f"[WARNING] Container {container.name} not found. It may have already been removed.")
    except docker.errors.DockerException as e:
        print(f"[ERROR] Failed to cleanup containers: {e}")
        
def stop_service(mgr, service_name):
    """
    Stops a running service by removing all its containers and network flows.
    """
    try:
        active_services = []
        for host in mgr.net.hosts:
            active_services.extend(mgr.getContainersDhost(host.name))

        matching_services = [s for s in active_services if service_name in s]

        if not matching_services:
            print(f"[ERROR] No running instances of '{service_name}' found.")
            return

        for service in matching_services:
            mgr.removeContainer(service)
            print(f"[INFO] Stopped service: {service}")

            # Extract host from service name (format: service_host)
            try:
                src_host = service.split('_')[1]
                src_ip = mgr.net.get(src_host).IP()
                switch = get_switch_for_host(mgr.net, src_host)

                # Remove associated flows
                for flow in list(flows.keys()):
                    if src_ip in flow:
                        remove_flow(switch, flow[0], flow[1])

                # Redeploy "colab" service on the host if there is space
                if len(mgr.getContainersDhost(src_host)) < 2:
                    if src_host not in container_counter:
                        container_counter[src_host] = {}
                    if "colab" not in container_counter[src_host]:
                        container_counter[src_host]["colab"] = 0
                    container_counter[src_host]["colab"] += 1
                    colab_container_name = f"colab_{src_host}_{container_counter[src_host]['colab']}"
                    mgr.addContainer(colab_container_name, src_host, "nginx:alpine", "nginx", docker_args={})
                    print(f"[INFO] Colab service redeployed on {src_host}")

            except IndexError:
                print("[ERROR] Service names must be in the format 'service_host'.")
            except KeyError as e:
                print(f"[ERROR] Invalid source host: {e}")
            except AttributeError as e:
                print(f"[ERROR] Failed to get switch for host: {e}")

        print(f"[INFO] Successfully stopped '{service_name}' and removed associated flows.")

    except ValueError as e:
        print(f"[ERROR] Failed to stop service {service_name}: {e}")
