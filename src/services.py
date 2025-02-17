import docker
import random
import requests
import subprocess
import json
import os

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
        ("database", 
            "import os; "
            "os.system('python3 /shared/scripts/database.py')"),
        ("webserver", 
            "import os; "
            "os.system('python3 /shared/scripts/web_server.py')")  
    ],
    "random": [
        ("random_gen1", 
            "import os; "
            "os.system('python3 /shared/scripts/random_gen1.py')"),
        ("random_gen2", 
            "import os; "
            "os.system('python3 /shared/scripts/random_gen2.py')"),
        ("random_sum", 
            "import os; "
            "os.system('python3 /shared/scripts/random_sum.py')")
    ],
    "datetime": [
        ("date_fetcher", 
            "import os; "
            "os.system('python3 /shared/scripts/date_fetcher.py')"),
        ("time_fetcher", 
            "import os; "
            "os.system('python3 /shared/scripts/time_fetcher.py')"),
        ("datetime_combiner", 
            "import os; "
            "os.system('python3 /shared/scripts/datetime_combiner.py')")
    ],
    "colab": [
        ("colab_a", 
            "import os; "
            "os.makedirs('/shared', exist_ok=True); "
            "service_key = os.getenv('SERVICE_KEY', 'unknown'); "
            "log_file = f'/shared/{service_key}.log'; "
            "open(log_file, 'a').write('colab_a says hi!\\n')"),
        ("colab_b", 
            "import os; "
            "os.makedirs('/shared', exist_ok=True); "
            "service_key = os.getenv('SERVICE_KEY', 'unknown'); "
            "log_file = f'/shared/{service_key}.log'; "
            "open(log_file, 'a').write('colab_b says hi too!\\n')")
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

    scripts_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'scripts'))
    
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
            if app_name == "database":
                # db_ip = mgr.net.get(host).IP()
                db_ip = container_name
                print(f"[INFO] Database IP: {db_ip}")
                process_cmd = ["python3", "/shared/scripts/database.py"]
            elif app_name == "webserver":
                process_cmd = ["python3", "/shared/scripts/web_server.py", f"http://{db_ip}:81"]
            else:
                process_cmd = ["python3", "-c", command.replace('localhost', mgr.net.get(host).IP())]
            env_vars = {
                "SERVICE_KEY": service_key,
                "HOSTNAME": "0.0.0.0", # mgr.net.get(host).IP(),
                "NAME": container_name
            }
            mgr.addContainer(container_name, host, "auto_deployment", process_cmd, docker_args={
                "command": process_cmd, 
                "volumes": {
                    "/shared": {"bind": "/shared", "mode": "rw"},
                    scripts_path : {"bind": "/shared/scripts", "mode": "ro"} 
                },
                "environment": env_vars,
                "network": "bridge",
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

        scripts_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'scripts'))
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
                process_cmd = ["python3", "-c", command.replace('localhost', container_name)]
                mgr.addContainer(container_name, host, "auto_deployment", process_cmd, docker_args={
                    "command": process_cmd, 
                    "volumes": {
                        "/shared": {"bind": "/shared", "mode": "rw"},
                        scripts_path : {"bind": "/shared/scripts", "mode": "ro"} 
                    },
                    "environment": {"SERVICE_KEY": service_key},
                    "network": "bridge",
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
    try:
        flow_rule = f"priority=100,ip,nw_src={src_ip},nw_dst={dst_ip},actions=output:{out_port}"
        switch.dpctl('add-flow', flow_rule)
        flows[(src_ip, dst_ip)] = (switch, in_port, out_port)
        print(f"[INFO] Flow added: {src_ip} -> {dst_ip}")
    except Exception as e:
        print(f"[ERROR] Failed to add flow: {src_ip} -> {dst_ip}. Error: {e}")

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
def test_services(mgr):
    """
    Tests the deployed services by checking their functionality and summarizing the results for each service.
    """
    test_results = {}

    for service_key, service_info in service_instances.items():
        service_name = service_key.split('_')[0]

        try:
            if service_name == "colab":
                log_file_path = f"/shared/{service_key}.log"
                with open(log_file_path, "r") as f:
                    result = f.read().strip()
                if not result:
                    result = "Colab log file is empty or not written correctly."
                test_results[service_key] = result.strip()

            elif service_name == "web":
                web_server_process = next((p for p in service_info["processes"] if "webserver" in p), None)
                db_server_process = next((p for p in service_info["processes"] if "database" in p), None)
                
                if web_server_process and db_server_process:
                    web_ip = get_container_ip(web_server_process)
                    db_ip = get_container_ip(db_server_process)
                    n = random.randint(1, 3)
                    web_url = f"http://{web_ip}:80"
                    db_url = f"http://{db_ip}:81/{n}"  

                    print(f"[DEBUG] Expected web_url: {web_url}")
                    print(f"[DEBUG] Expected db_url: {db_url}")

                    try:
                        web_response = requests.get(web_url, timeout=10)
                        db_response = requests.get(db_url, timeout=10)

                        if web_response.status_code == 200 and db_response.status_code == 200:
                            result = f"Web service running. DB Response: {db_response.text[:100]}"
                        else:
                            result = f"Web or DB service failed. Web: {web_response.status_code}, DB: {db_response.status_code}"
                    except requests.ConnectionError as e:
                        result = f"Error: Could not connect to one of the services. {e}"
                    except requests.Timeout:
                        result = "Error: Request to one of the services timed out."
                else:
                    result = "Web or Database service is missing"
                test_results[service_key] = result.strip()
            elif service_name == "random":
                result_file_path = f"/shared/{service_key}.txt"
                with open(result_file_path, "r") as f:
                    result = f.read().strip()
                if not result:
                    result = "Random result file is empty or not written correctly."
                test_results[service_key] = result.strip()

            elif service_name == "datetime":
                result_file_path = f"/shared/{service_key}.txt"
                with open(result_file_path, "r") as f:
                    result = f.read().strip()
                if not result:
                    result = "Datetime result file is empty or not written correctly."
                test_results[service_key] = result.strip()

            else:
                test_results[service_key] = "Unknown service type"

        except FileNotFoundError:
            test_results[service_key] = f"{service_name} result file not found."
        except Exception as e:
            test_results[service_key] = f"Error reading {service_name} result file: {e}"

    # Print the summarized results
    print("\n--- Test Results Summary ---\n")
    for service_key, result in test_results.items():
        print(f"Service: {service_key}")
        print(f"  - Result: {result}")
        print("\n" + "-"*30 + "\n")

    return test_results

def get_container_ip(container_name):
    # Run the docker network inspect command to get the details in JSON format
    result = subprocess.run(
        ['docker', 'network', 'inspect', 'bridge'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    # Parse the JSON response
    network_info = json.loads(result.stdout)

    # Find the container info by matching the container name
    for container in network_info[0]['Containers']:
        if container_name in network_info[0]['Containers'][container]['Name']:
            # Return the IP address of the container
            return network_info[0]['Containers'][container]['IPv4Address'].split('/')[0]

    # Return None if not found
    return None

def clean_shared_folder():
    """
    Clean up the /shared folder by deleting all files except the scripts directory.
    """
    shared_folder = "/shared"
    if os.path.exists(shared_folder):
        for filename in os.listdir(shared_folder):
            file_path = os.path.join(shared_folder, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path) and filename != "scripts":
                    os.rmdir(file_path)
            except Exception as e:
                print(f"[ERROR] Failed to delete {file_path}. Reason: {e}")