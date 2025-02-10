import docker
import random
import subprocess

# Track flows between services
flows = {}
container_counter = {}
service_instances = {}
should_deploy_colab = True

service_counters = {
    "web": 0,
    "random": 0,
    "datetime": 0,
    "colab": 0
}
service_definitions = {
    "web": [
        ("database", "python3 -c 'import os; os.makedirs(\"/shared\", exist_ok=True); "
                     "subprocess.Popen([\"python3\", \"-m\", \"http.server\", \"81\"])'"),
        ("webserver", "python3 -c 'import os, time, requests, http.server; "
                      "class Handler(http.server.SimpleHTTPRequestHandler): "
                      "    def do_GET(self): "
                      "        try: "
                      "            data = requests.get(\"http://localhost:81\").text; "
                      "            self.send_response(200); "
                      "            self.send_header(\"Content-type\", \"text/html\"); "
                      "            self.end_headers(); "
                      "            self.wfile.write(f\"<html><body><h1>Data from DB:</h1><p>{data}</p></body></html>\".encode()); "
                      "        except Exception as e: "
                      "            self.send_response(500); "
                      "            self.end_headers(); "
                      "            self.wfile.write(f\"<html><body><h1>Error:</h1><p>{e}</p></body></html>\".encode()); "
                      "http.server.HTTPServer((\"\", 80), Handler).serve_forever()'")
    ],
    "random": [
        ("random_gen1", "python3 -c 'import os, random; os.makedirs(\"/shared\", exist_ok=True); "
                        "open(\"/shared/random_gen1.txt\", \"w\").write(str(random.randint(1, 100)))'"),
        ("random_gen2", "python3 -c 'import os, random; os.makedirs(\"/shared\", exist_ok=True); "
                        "open(\"/shared/random_gen2.txt\", \"w\").write(str(random.randint(1, 100)))'"),
        ("random_sum", "python3 -c 'import os; os.makedirs(\"/shared\", exist_ok=True); "
                       "open(\"/shared/random_gen1.txt\", \"a\").close(); "
                       "open(\"/shared/random_gen2.txt\", \"a\").close(); "
                       "a = int(open(\"/shared/random_gen1.txt\").read()); "
                       "b = int(open(\"/shared/random_gen2.txt\").read()); "
                       "open(\"/shared/random_result.txt\", \"w\").write(f\"{a} + {b} = {a+b}\")'"),
    ],
    "datetime": [
        ("date_fetcher", "python3 -c 'import os, datetime; os.makedirs(\"/shared\", exist_ok=True); "
                         "open(\"/shared/date.txt\", \"w\").write(str(datetime.datetime.now().date()))'"),
        ("time_fetcher", "python3 -c 'import os, datetime; os.makedirs(\"/shared\", exist_ok=True); "
                         "open(\"/shared/time.txt\", \"w\").write(str(datetime.datetime.now().time()))'"),
        ("datetime_combiner", "python3 -c 'import os; os.makedirs(\"/shared\", exist_ok=True); "
                              "date = open(\"/shared/date.txt\").read(); "
                              "time = open(\"/shared/time.txt\").read(); "
                              "open(\"/shared/datetime_result.txt\", \"w\").write(f\"{date} {time}\")'"),
    ],
    "colab": [
        ("colab_a", "python3 -c 'import os, time; os.makedirs(\"/var/log\", exist_ok=True); "
                    "log_file = \"/var/log/colab.log\"; "
                    "while True: "
                    "    open(log_file, \"a\").write(\"colab_a says hi!\\n\"); "
                    "    time.sleep(1)'"),
        ("colab_b", "python3 -c 'import os, time; os.makedirs(\"/var/log\", exist_ok=True); "
                    "log_file = \"/var/log/colab.log\"; "
                    "while True: "
                    "    open(log_file, \"a\").write(\"colab_b replies hello!\\n\"); "
                    "    time.sleep(1)'"),
    ]
}


# set up docker images and cleanup
def setup_docker_images():
    """
    Ensure 'auto_deployment' Docker image is available before starting containers.
    """
    client = docker.from_env()
    image_name = "auto_deployment"

    try:
        print(f"[INFO] Checking if image '{image_name}' is available locally...")
        if not client.images.list(name=image_name):
            print(f"[ERROR] Image '{image_name}' is missing! Please build it using:")
            print("       docker build -t auto_deployment .")
            exit(1)  # Stop execution if the image is missing
        else:
            print(f"[INFO] Image '{image_name}' is available locally.")
    except docker.errors.DockerException as e:
        print(f"[ERROR] Docker is not running or failed to check images: {e}")
        exit(1)

def cleanup_containers():
    """
    Stop and remove Docker containers
    """
    client = docker.from_env()
    try:
        containers = client.containers.list(all=True)
        for container in containers:
            print(f"[INFO] Stopping and removing container: {container.name}")
            try:
                container.stop()
                container.remove()
            except docker.errors.NotFound:
                print(f"[WARNING] Container {container.name} not found. It may have already been removed.")
    except docker.errors.DockerException as e:
        print(f"[ERROR] Failed to cleanup containers: {e}")

# services deploy and stop
def deploy_service(mgr, service_name):
    """
    Deploys a service, choosing hosts automatically.
    """
    global should_deploy_colab

    if service_name not in service_definitions:
        print(f"[ERROR] Service '{service_name}' not supported.")
        return

    required_hosts = len(service_definitions[service_name])
    available_hosts = get_available_hosts(mgr)

    # Ensure there are enough hosts by removing "colab" services if necessary
    if len(available_hosts) < required_hosts:
        colab_services_to_remove = []
        for service_key, service_info in service_instances.items():
            if "colab" in service_key:
                colab_services_to_remove.append(service_key)
                if len(colab_services_to_remove) * 2 >= required_hosts:
                    break

        for service_key in colab_services_to_remove:
            service_info = service_instances[service_key]
            for service in service_info["processes"]:
                mgr.removeContainer(service)
                print(f"[INFO] Removed colab service: {service}")

            del service_instances[service_key]
            available_hosts = get_available_hosts(mgr)
            if len(available_hosts) >= required_hosts:
                break

    if len(available_hosts) < required_hosts:
        print("[ERROR] Not enough available hosts even after removing colab services!")
        return

    selected_hosts = random.sample(available_hosts, required_hosts)
    service_counters[service_name] += 1
    service_key = f"{service_name}_{service_counters[service_name]}"
    service_instances[service_key] = {
        "processes": [],
        "flows": []
    }

    for (app_name, command), host in zip(service_definitions[service_name], selected_hosts):
        if len(mgr.getContainersDhost(host)) == 2:
            print(f"[ERROR] Host {host} already has 2 containers.")
            continue
        if host not in container_counter:
            container_counter[host] = {}
        if app_name not in container_counter[host]:
            container_counter[host][app_name] = 0
        container_counter[host][app_name] += 1
        container_name = f"{app_name}_{host}_{container_counter[host][app_name]}"
        try:
            process_cmd = ["python3", "-c", command]
            mgr.addContainer(container_name, host, "python:3.8-slim", process_cmd, docker_args={
                "command": process_cmd, 
                "volumes": {"/shared": {"bind": "/shared", "mode": "rw"}}
            })
            service_instances[service_key]["processes"].append(container_name)
            print(f"[INFO] Service {app_name} started on {host}")
        except Exception as e:
            print(f"[ERROR] Failed to start service {app_name} on {host}: {e}")

    setup_service_flows(mgr.net, service_definitions[service_name], selected_hosts, service_key)
    
    total_containers = sum(len(mgr.getContainersDhost(host.name)) for host in mgr.net.hosts)
    max_containers = len(mgr.net.hosts) * 2
    if total_containers < max_containers:
        should_deploy_colab = True

    # Call deploy_colab_service if needed after deploying the service
    if should_deploy_colab:
        deploy_colab_service(mgr)

def deploy_colab_service(mgr):
    """
    Deploys or redeploys colab services on available hosts dynamically.
    Colab services should use all available resources but give priority to user deployable services.
    """
    global should_deploy_colab

    while should_deploy_colab:
        available_hosts = get_available_hosts(mgr)

        if len(available_hosts) < 1:
            print("[INFO] No available spaces to deploy colab services.")
            return
        elif len(available_hosts) == 1 and len(mgr.getContainersDhost(available_hosts[0])) == 0:
            # If only one host is available but has two free slots, deploy both services there.
            selected_hosts = [available_hosts[0], available_hosts[0]]
        elif len(available_hosts) >= 2:
            # If at least two hosts are available, deploy on different hosts.
            selected_hosts = random.sample(available_hosts, 2)
        else:
            # If only one slot is available, wait until more slots are available.
            print("[INFO] Not enough space to deploy a full colab service. Waiting...")
            return

        service_counters["colab"] += 1
        service_key = f"colab_{service_counters['colab']}"
        service_instances[service_key] = {
            "processes": [],
            "flows": []
        }

        for (app_name, command), host in zip(service_definitions["colab"], selected_hosts):
            if len(mgr.getContainersDhost(host)) == 2:
                print(f"[INFO] Skipping {host}, already has 2 containers.")
                continue  # Don't deploy if the host is full

            if host not in container_counter:
                container_counter[host] = {}
            if app_name not in container_counter[host]:
                container_counter[host][app_name] = 0
            container_counter[host][app_name] += 1

            container_name = f"{app_name}_{host}_{container_counter[host][app_name]}"

            try:
                process_cmd = ["python3", "-c", command]
                mgr.addContainer(container_name, host, "auto_deployment", process_cmd, docker_args={
                    "command": process_cmd, 
                    "volumes": {"/shared": {"bind": "/shared", "mode": "rw"}}
                })
                service_instances[service_key]["processes"].append(container_name)
                print(f"[INFO] Colab service {app_name} started on {host}")
            except Exception as e:
                print(f"[ERROR] Failed to start colab service {app_name} on {host}: {e}")

        setup_service_flows(mgr.net, service_definitions["colab"], selected_hosts, service_key)
    should_deploy_colab = False

def stop_service(mgr, selected_process, service_instances):
    """
    Stops a specific service and removes associated flows.
    """
    stopped_services = []
    removed_flows = []
    global should_deploy_colab

    service_key = None
    for key, value in service_instances.items():
        if selected_process in value["processes"]:
            service_key = key
            break

    if not service_key:
        print(f"[ERROR] Service for process '{selected_process}' not found in service_instances.")
        return stopped_services, removed_flows

    service_info = service_instances[service_key]

    for service in service_info["processes"]:
        mgr.removeContainer(service)
        stopped_services.append(service)
        print(f"[INFO] Stopped service: {service}")

        # Extract host from service name (format: service_host)
        try:
            src_host = service.split('_')[2] 
            src_ip = mgr.net.get(src_host).IP()
            switch = get_switch_for_host(mgr.net, src_host)

            # Remove associated flows
            for flow in service_info["flows"]:
                if src_ip in flow["src_ip"]:
                    remove_flow(switch, flow["src_ip"], flow["dst_ip"])
                    removed_flows.append((flow["src_ip"], flow["dst_ip"]))

        except IndexError:
            print("[ERROR] Service names must be in the format 'service_host'.")
        except KeyError as e:
            print(f"[ERROR] Invalid source host: {e}")
        except AttributeError as e:
            print(f"[ERROR] Failed to get switch for host: {e}")

    del service_instances[service_key]
    print(f"[INFO] Successfully stopped '{service_key}' and removed associated flows.")
        
    # Ensure colab services can be redeployed if needed
    total_containers = sum(len(mgr.getContainersDhost(host.name)) for host in mgr.net.hosts)
    max_containers = len(mgr.net.hosts) * 2
    if total_containers < max_containers:
        should_deploy_colab = True
        
    return stopped_services, removed_flows

def setup_service_flows(net, service_apps, hosts, service_key):
    """
    Configures SDN flows to enable communication between service components.
    """
    if len(hosts) < 2:
        print("[ERROR] Not enough hosts to set up flows.")
        return

    for i in range(len(service_apps) - 1):
        # Ensure we don't go out of bounds
        if i + 1 >= len(hosts):  
            break
        
        src_host = hosts[i]
        dst_host = hosts[i + 1]
        src_ip = net.get(src_host).IP()
        dst_ip = net.get(dst_host).IP()
        switch = get_switch_for_host(net, src_host)

        if switch:
            in_port = 1
            out_port = 2
            setup_flow(switch, src_ip, dst_ip, in_port, out_port)
            service_instances[service_key]["flows"].append({
                "src_ip": src_ip,
                "dst_ip": dst_ip,
                "switch": switch.name,
                "in_port": in_port,
                "out_port": out_port
            })
            print(f"[INFO] Flow configured between {src_host} and {dst_host}")

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

def update_gui_with_active_flows():
    """
    Updates the GUI with only the active flows and services.
    """
    results = {
        "flows": {},
        "services": {}
    }

    # Debugging: Print all active flows
    print("[DEBUG] Active Flows:")
    for service_key, service_info in service_instances.items():
        for flow in service_info["flows"]:
            results["flows"][(service_key, flow["src_ip"], flow["dst_ip"])] = {
                "switch": flow["switch"],
                "in_port": flow["in_port"],
                "out_port": flow["out_port"]
            }
            print(f"  - {service_key}: {flow['src_ip']} -> {flow['dst_ip']} (Switch: {flow['switch']})")

    # Debugging: Print all active services
    print("[DEBUG] Active Services:")
    for service_key, service_info in service_instances.items():
        results["services"][service_key] = service_info["processes"]
        print(f"  - {service_key}: {service_info['processes']}")

    return results

def get_available_hosts(mgr):
    """
    Get a list of available hosts with less than 2 containers.
    """
    return [host.name for host in mgr.net.hosts if len(mgr.getContainersDhost(host.name)) < 2]


# manager of services interacting with gui
def control_services(mgr, action, service_name=None, selected_process=None, gui=None):
    """
    Controls the deployment, stopping, and redeployment of services based on GUI interactions.
    action: Action to perform ('deploy', 'stop','redeploy_colab')
    """
    global should_deploy_colab

    if action == 'deploy' and service_name:
        deploy_service(mgr, service_name)
    elif action == 'stop' and selected_process:
        stopped_services, removed_flows = stop_service(mgr, selected_process, service_instances)
        if should_deploy_colab:
            deploy_colab_service(mgr)
        if gui:
            gui.update_active_services_listbox()
            gui.update_communication_results()
        return stopped_services, removed_flows
    elif action == 'redeploy_colab':
        deploy_colab_service(mgr)
    else:
        print("[ERROR] Invalid action or missing parameters.")
        return [], []

    if gui:
        gui.update_active_services_listbox()
        gui.update_communication_results()


# test services 
def test_services(mgr, net, gui):
    """
    Tests the deployed services and updates the GUI with the results.
    """
    test_results = []

    for service_key, service_info in service_instances.items():
        service_name = service_key.split('_')[0]

        for process in service_info["processes"]:
            try:
                host_name = process.split('_')[2]  # Extract the host name
                host = net.get(host_name)

                if service_name == "colab":
                    result = host.cmd("tail -n 5 /var/log/colab.log")  
                elif service_name == "web":
                    result = host.cmd("curl -s -o /dev/null -w '%{http_code}' http://localhost:80")  
                elif service_name == "random":
                    result = host.cmd("cat /shared/random_result.txt")
                elif service_name == "datetime":
                    result = host.cmd("cat /shared/datetime_result.txt")
                else:
                    result = "Unknown service type"

                test_results.append(f"Service: {service_key}, Process: {process}, Result: {result.strip()}")
                print(f"Service: {service_key}, Process: {process}, Result: {result.strip()}")

            except Exception as e:
                test_results.append(f"Service: {service_key}, Process: {process}, Error: {e}")
                print(f"[ERROR] Service: {service_key}, Process: {process}, Error: {e}")

    return test_results

