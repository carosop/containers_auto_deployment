import docker
import os

# Track flows between services
flows = {}

def setup_docker_images():
    """
    Prepare required Docker images. Pull missing images.
    """
    client = docker.from_env()
    images = ["httpd:alpine", "nginx:alpine", "mysql:latest"]
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

def deploy_service(mgr, service_name, image, command, host):
    """
    Deploy a service on a specified host with application limits.
    """
    running_containers = mgr.getContainersDhost(host)
    if len(running_containers) >= 2:  # Max 2 applications per host
        print(f"[ERROR] Host {host} has reached its container limit.")
        return

    base_service_name = f"{service_name}_{host}"
    counter = len(running_containers) + 1
    unique_service_name = f"{base_service_name}_{counter}"

    try:
        mgr.addContainer(unique_service_name, host, image, command, docker_args={})
        print(f"[INFO] Service {unique_service_name} deployed on {host}")
    except docker.errors.APIError as e:
        if e.status_code == 409:  # Conflict error
            print(f"[ERROR] Container name conflict: {e.explanation}")
        else:
            print(f"[ERROR] Failed to deploy service {unique_service_name}: {e}")

def stop_service(mgr, service_name):
    """
    Stop a running service by removing its container.
    """
    try:
        mgr.removeContainer(service_name)
        print(f"[INFO] Service {service_name} stopped.")
        # Remove associated flows
        for flow in list(flows.keys()):
            if service_name in flow:
                remove_flow(flow[0], flow[1])
    except ValueError as e:
        print(f"[ERROR] Failed to stop service {service_name}: {e}")

def setup_flow(switch, src_ip, dst_ip, in_port, out_port):
    """
    Set up a flow between two hosts in the SDN network.
    """
    flow_rule = f"priority=100,ip,nw_src={src_ip},nw_dst={dst_ip},actions=output:{out_port}"
    reverse_flow_rule = f"priority=100,ip,nw_src={dst_ip},nw_dst={src_ip},actions=output:{in_port}"

    try:
        if (src_ip, dst_ip) not in flows:
            switch.dpctl('add-flow', flow_rule)
            switch.dpctl('add-flow', reverse_flow_rule)
            flows[(src_ip, dst_ip)] = flow_rule
            flows[(dst_ip, src_ip)] = reverse_flow_rule
            print(f"[INFO] Configured flow between {src_ip} and {dst_ip}.")
        else:
            print(f"[INFO] Flow already exists between {src_ip} and {dst_ip}.")
    except Exception as e:
        print(f"[ERROR] Failed to set flow between {src_ip} and {dst_ip}: {e}")

def remove_flow(switch, src_ip, dst_ip):
    """
    Remove OpenFlow rules when service is stopped.
    """
    flow_rule = f"ip,nw_src={src_ip},nw_dst={dst_ip}"
    reverse_flow_rule = f"ip,nw_src={dst_ip},nw_dst={src_ip}"

    try:
        if (src_ip, dst_ip) in flows:
            switch.dpctl('del-flows', flow_rule)
            switch.dpctl('del-flows', reverse_flow_rule)
            flows.pop((src_ip, dst_ip), None)
            flows.pop((dst_ip, src_ip), None)
            print(f"[INFO] Removed flow between {src_ip} and {dst_ip}.")
        else:
            print(f"[INFO] No flow exists between {src_ip} and {dst_ip}.")
    except Exception as e:
        print(f"[ERROR] Failed to remove flow between {src_ip} and {dst_ip}: {e}")

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