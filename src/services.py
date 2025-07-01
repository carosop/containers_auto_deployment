import os
import time
import signal
import subprocess
import random
from flow import FlowManager

class ServiceManager:
    def __init__(self, controller=None):
        self.service_instances = {}  # (service_key, app_name): {host, process, ip, listen_port}
        self.host_app_counts = {}
        self.host_max_apps = 2
        self.flow_manager = FlowManager()
        self.active_flows = {}
        self.service_counters = {k: 0 for k in ["web", "random", "datetime", "colab"]}
        self.service_definitions = {
            "web": [
                ("database", "python3 /shared/scripts/database.py", {"LISTEN_PORT": "81"}),
                ("web_server", "python3 /shared/scripts/web_server.py", {"DB_IP": None, "LISTEN_PORT": "80"})
            ],
            "random": [
                ("random_gen1", "python3 /shared/scripts/random_gen1.py", {"LISTEN_PORT": "5000"}),
                ("random_gen2", "python3 /shared/scripts/random_gen2.py", {"LISTEN_PORT": "5001"}),
                ("random_sum", "python3 /shared/scripts/random_sum.py", {"GEN1_IP": None, "GEN2_IP": None, "LISTEN_PORT": "8080"})
            ],
            "datetime": [
                ("date_fetcher", "python3 /shared/scripts/date_fetcher.py", {"LISTEN_PORT": "5002"}),
                ("time_fetcher", "python3 /shared/scripts/time_fetcher.py", {"LISTEN_PORT": "5003"}),
                ("datetime_combiner", "python3 /shared/scripts/datetime_combiner.py", {"DATE_IP": None, "TIME_IP": None, "LISTEN_PORT": "8081"})
            ],
            "colab": [
                ("colab_a", "python3 /shared/scripts/colab_a.py", {"COLAB_B_IP": None, "LISTEN_PORT": "8082"}),
                ("colab_b", "python3 /shared/scripts/colab_b.py", {"LISTEN_PORT": "5004"})
            ]
        }
        self.controller = controller
        self.flow_modification_queue = None  # or queue.Queue() if you use it directly

    def get_flow_queue(self):
        return self.flow_modification_queue

    def _find_available_host(self, net, service_key, used_hosts=None):
        # used_hosts: set of host names already used for this service_key
        if used_hosts is None:
            used_hosts = set()
        candidates = [host for host in net.hosts
                      if self.host_app_counts.get(host.name, 0) < self.host_max_apps
                      and host.name not in used_hosts]
        if candidates:
            return random.choice(candidates)
        return None

    def deploy_service_instance(self, net, service_key, app_name, command, env_vars, host=None, used_hosts=None):
        if not host:
            host = self._find_available_host(net, service_key, used_hosts)
        if not host:
            print(f"[ERROR] No available host for {service_key}-{app_name}")
            return False
        env = {line.split('=', 1)[0]: line.split('=', 1)[1] for line in host.cmd("env").strip().split('\n') if '=' in line}
        env.update({k: v for k, v in env_vars.items() if v is not None})
        env["SERVICE_KEY"] = service_key
        cmd_args = command.split()
        try:
            proc = host.popen(cmd_args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setsid, env=env)
            self.service_instances[(service_key, app_name)] = {
                "host": host,
                "process": proc,
                "ip": host.IP(),
                "listen_port": int(env_vars.get("LISTEN_PORT", 0))
            }
            self.host_app_counts[host.name] = self.host_app_counts.get(host.name, 0) + 1
            print(f"[INFO] {app_name} of {service_key} deployed on {host.name} ({host.IP()})")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to deploy {app_name}: {e}")
            return False

    def stop_service_instance(self, service_key):
        # Stop all apps for this service_key
        for (s_k, a_n) in list(self.service_instances.keys()):
            if s_k == service_key:
                inst = self.service_instances[(s_k, a_n)]
                proc = inst["process"]
                host = inst["host"]
                try:
                    if proc and proc.poll() is None:
                        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                        time.sleep(0.5)
                        if proc.poll() is None:
                            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                        proc.wait(timeout=1)
                except Exception as e:
                    print(f"[ERROR] Error terminating {a_n}: {e}")
                self.host_app_counts[host.name] = max(0, self.host_app_counts.get(host.name, 1) - 1)
                del self.service_instances[(s_k, a_n)]
        self._remove_flows_for_service(service_key)
        return True

    def _remove_flows_for_service(self, service_key):
        flows = self.flow_manager.get_active_flows()
        for (s_k, src_ip, dst_ip, dst_port, proto, dpid, in_port), flow in list(flows.items()):
            if s_k == service_key:
                self.flow_manager.remove_flow_queue(self.flow_modification_queue, service_key, src_ip, dst_ip, proto, None, dst_port)

    def _install_flows_for_service(self, net, service_key):
        apps = {app: inst for (s_k, app), inst in self.service_instances.items() if s_k == service_key}
        TCP = 6
        ICMP = 1
        hosts = [inst["host"] for inst in apps.values()]
        # ICMP flows between all pairs (for ping)
        for i in range(len(hosts)):
            for j in range(i+1, len(hosts)):
                self.flow_manager.add_flow_queue(
                    self.flow_modification_queue, net, service_key,
                    hosts[i], hosts[j], ICMP
                )
        # Service-specific TCP flows and env updates
        if service_key.startswith("web"):
            db, web = apps.get("database"), apps.get("web_server")
            if db and web:
                self.flow_manager.add_flow_queue(self.flow_modification_queue, net, service_key, web["host"], db["host"], TCP, None, db["listen_port"])
                self._restart_app(web, self.service_definitions["web"][1][1], {"DB_IP": db["ip"], "SERVICE_KEY": service_key})
        elif service_key.startswith("random"):
            g1, g2, summ = apps.get("random_gen1"), apps.get("random_gen2"), apps.get("random_sum")
            if g1 and g2 and summ:
                self.flow_manager.add_flow_queue(self.flow_modification_queue, net, service_key, summ["host"], g1["host"], TCP, None, g1["listen_port"])
                self.flow_manager.add_flow_queue(self.flow_modification_queue, net, service_key, summ["host"], g2["host"], TCP, None, g2["listen_port"])
                self._restart_app(summ, self.service_definitions["random"][2][1], {"GEN1_IP": g1["ip"], "GEN2_IP": g2["ip"], "SERVICE_KEY": service_key})
        elif service_key.startswith("datetime"):
            date, timef, comb = apps.get("date_fetcher"), apps.get("time_fetcher"), apps.get("datetime_combiner")
            if date and timef and comb:
                self.flow_manager.add_flow_queue(self.flow_modification_queue, net, service_key, comb["host"], date["host"], TCP, None, date["listen_port"])
                self.flow_manager.add_flow_queue(self.flow_modification_queue, net, service_key, comb["host"], timef["host"], TCP, None, timef["listen_port"])
                self._restart_app(comb, self.service_definitions["datetime"][2][1], {"DATE_IP": date["ip"], "TIME_IP": timef["ip"], "SERVICE_KEY": service_key})
        elif service_key.startswith("colab"):
            a, b = apps.get("colab_a"), apps.get("colab_b")
            if a and b:
                self.flow_manager.add_flow_queue(self.flow_modification_queue, net, service_key, a["host"], b["host"], TCP, None, b["listen_port"])
                self._restart_app(a, self.service_definitions["colab"][0][1], {"COLAB_B_IP": b["ip"], "SERVICE_KEY": service_key})

    def _restart_app(self, inst, command, env_updates):
        proc = inst["process"]
        host = inst["host"]
        try:
            if proc and proc.poll() is None:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                time.sleep(0.5)
                if proc.poll() is None:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                proc.wait(timeout=1)
        except Exception:
            pass
        env = {line.split('=', 1)[0]: line.split('=', 1)[1] for line in host.cmd("env").strip().split('\n') if '=' in line}
        env.update(env_updates)
        cmd_args = command.split()
        new_proc = host.popen(cmd_args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setsid, env=env)
        inst["process"] = new_proc

    def control_services(self, net, action, service_name=None, selected_process=None, gui=None):
        if action == "deploy":
            if not service_name:
                print("[ERROR] Service name required.")
                return
            app_defs = self.service_definitions.get(service_name)
            needed_slots = len(app_defs)
            available_slots = sum(self.host_max_apps - self.host_app_counts.get(h.name, 0) for h in net.hosts)
            # If not enough space, stop as many colab instances as needed
            if available_slots < needed_slots and service_name != "colab":
                colab_keys = sorted({k[0] for k in self.service_instances if k[0].startswith("colab")})
                stopped = 0
                for colab_key in colab_keys:
                    if available_slots >= needed_slots:
                        break
                    if self.stop_service_instance(colab_key):
                        stopped += 1
                        available_slots = sum(self.host_max_apps - self.host_app_counts.get(h.name, 0) for h in net.hosts)
                if available_slots < needed_slots:
                    print("[ERROR] Not enough space to deploy the service, even after stopping colab.")
                    if gui:
                        gui.test_results_text.config(state="normal")
                        gui.test_results_text.insert("end", "Not enough space to deploy the service.\n")
                        gui.test_results_text.config(state="disabled")
                    return
            self.service_counters[service_name] += 1
            service_key = f"{service_name}-{self.service_counters[service_name]}"
            used_hosts = set()
            for idx, (app_name, command, env_vars) in enumerate(app_defs):
                host = self._find_available_host(net, service_key, used_hosts)
                # Fallback: if not enough hosts, allow reuse for this service instance
                if not host and used_hosts:
                    host = self._find_available_host(net, service_key)
                if not self.deploy_service_instance(net, service_key, app_name, command, env_vars.copy(), host=host):
                    print(f"[ERROR] Failed to deploy {app_name} for {service_key}. Rolling back.")
                    self.stop_service_instance(service_key)
                    return
                if host:
                    used_hosts.add(host.name)
            self._install_flows_for_service(net, service_key)
            self._update_controller_service_members() # Keep if you use it for other controller logic
            self.active_flows = self.flow_manager.get_active_flows() # Update local active flows from FlowManager
            print(f"[SUCCESS] Service '{service_key}' deployed.")
            if gui:
                gui.update_active_services()
                gui.update_communication_results()
        elif action == "stop":
            if not selected_process:
                print("[ERROR] No service instance selected to stop.")
                return
            parts = selected_process.split(', ')
            service_key = parts[0].split(': ')[1]
            if self.stop_service_instance(service_key):
                self._update_controller_service_members() # Keep if you use it for other controller logic
                self.try_redeploy_colab(net)
                print(f"[SUCCESS] Stopped {service_key}")
            if gui:
                gui.update_active_services()
                gui.update_communication_results()

    def deploy_colab_on_all_hosts(self, net):
        service_name = "colab"
        app_defs = self.service_definitions[service_name]
        used_hosts = set()
        for _ in net.hosts:
            service_key = f"colab-{len(self.service_instances)//len(app_defs)+1}"
            for app_name, command, env_vars in app_defs:
                host = self._find_available_host(net, service_key, used_hosts)
                # If no unused host, allow reuse for this service instance
                if not host and used_hosts:
                    host = self._find_available_host(net, service_key)
                if not self.deploy_service_instance(net, service_key, app_name, command, env_vars.copy(), host=host):
                    print(f"[ERROR] Failed to deploy {app_name} for {service_key}. Rolling back.")
                    self.stop_service_instance(service_key)
                    break
                if host:
                    used_hosts.add(host.name)
            self._install_flows_for_service(net, service_key)
        self._update_controller_service_members()

    def try_redeploy_colab(self, net):
        service_name = "colab"
        app_defs = self.service_definitions[service_name]
        used_hosts = set(h.name for (k, _), inst in self.service_instances.items() if k.startswith("colab"))
        for _ in net.hosts:
            # Find a service_key not already used
            idx = 1
            while f"colab-{idx}" in (k for (k, _) in self.service_instances):
                idx += 1
            service_key = f"colab-{idx}"
            # Find available host, prefer unused
            host = self._find_available_host(net, service_key, used_hosts)
            if not host and used_hosts:
                host = self._find_available_host(net, service_key)
            # Only deploy if host has enough space for both apps
            if host and self.host_app_counts.get(host.name, 0) <= self.host_max_apps - len(app_defs):
                for app_name, command, env_vars in app_defs:
                    self.deploy_service_instance(net, service_key, app_name, command, env_vars.copy(), host=host)
                self._install_flows_for_service(net, service_key)
                used_hosts.add(host.name)
        self._update_controller_service_members()

    def wait_for_file_content(self, host, filepath, timeout=20, interval=0.5):
        waited = 0
        while waited < timeout:
            check = host.cmd(f"test -s {filepath} && echo 'exists'").strip()
            print(f"[DEBUG] wait_for_file_content: waited={waited}, test output='{check}'")
            if check == "exists":
                content = host.cmd(f"cat {filepath}").strip()
                print(f"[DEBUG] wait_for_file_content: read content='{content}'")
                # Escludi "exists" come contenuto valido
                if content and content != "exists":
                    return content
            time.sleep(interval)
            waited += interval
        return None
    def test_service(self, net, service_key_to_test):
        test_results = {}
        client_map = {"web": "web_server", "random": "random_sum", "datetime": "datetime_combiner", "colab": "colab_a"}
        for prefix, client_app in client_map.items():
            if service_key_to_test.startswith(prefix):
                break
        else:
            test_results[service_key_to_test] = "Error: No client application defined."
            return test_results
        inst = next((info for (s_k, a_n), info in self.service_instances.items() if s_k == service_key_to_test and a_n == client_app), None)
        if inst:
            host = inst["host"]
            output_file = f"/shared/{service_key_to_test}.txt"
            content = self.wait_for_file_content(host, output_file)
            if content:
                test_results[service_key_to_test] = content
            else:
                test_results[service_key_to_test] = f"Error: Output file {output_file} missing or empty after waiting."
        else:
            test_results[service_key_to_test] = f"Error: Client app {client_app} not found."
        return test_results

    def clean_shared_folder(self):
        shared_folder = "/shared"
        if os.path.exists(shared_folder):
            for filename in os.listdir(shared_folder):
                file_path = os.path.join(shared_folder, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                except Exception as e:
                    print(f"[ERROR] Failed to delete {file_path}: {e}")
            print(f"[INFO] Cleaned up /shared folder.")

    def update_gui_with_active_services(self):
        return [f"Service: {s_k}, App: {a_n}, Host: {inst['host'].name}, IP: {inst['ip']}" for (s_k, a_n), inst in self.service_instances.items()]

    def update_gui_with_active_flows(self):
        self.active_flows = self.flow_manager.get_active_flows()
        return {"flows": self.active_flows}


    def _remove_flows_for_service(self, service_key):
        # The FlowManager now handles the direct API calls for removal
        flows = self.flow_manager.get_active_flows()
        flows_to_remove = []
        for (s_k, src_ip, dst_ip, dst_port, proto, dpid, in_port), flow in list(flows.items()):
            if s_k == service_key:
                flows_to_remove.append(flow) # Collect flows associated with the service_key
                
        # Call remove_flow_queue (which now calls _send_flow_to_ryu for removal) for each.
        # Note: You might want to pass more specific info to remove_flow_queue if you want to delete
        # by specific match fields rather than just the service_key.
        # The current remove_flow_queue in FlowManager will iterate and delete.
        for flow_data in flows_to_remove:
            self.flow_manager.remove_flow_queue(
                None, # No queue needed here
                service_key,
                flow_data['src_ip'],
                flow_data['dst_ip'],
                flow_data['protocol'],
                flow_data['src_port'],
                flow_data['dst_port']
            )

    def _install_flows_for_service(self, net, service_key):
        apps = {app: inst for (s_k, app), inst in self.service_instances.items() if s_k == service_key}
        TCP = 6
        ICMP = 1
        hosts = [inst["host"] for inst in apps.values()]
        
        # ICMP flows between all pairs (for ping)
        for i in range(len(hosts)):
            for j in range(i+1, len(hosts)):
                self.flow_manager.add_flow_queue( # No queue passed, FlowManager sends directly
                    None, # Queue argument becomes None as it's not used for direct API calls
                    net, service_key,
                    hosts[i], hosts[j], ICMP
                )
        # Service-specific TCP flows and env updates
        if service_key.startswith("web"):
            db, web = apps.get("database"), apps.get("web_server")
            if db and web:
                self.flow_manager.add_flow_queue(None, net, service_key, web["host"], db["host"], TCP, None, db["listen_port"])
                self._restart_app(web, self.service_definitions["web"][1][1], {"DB_IP": db["ip"], "SERVICE_KEY": service_key})
        elif service_key.startswith("random"):
            g1, g2, summ = apps.get("random_gen1"), apps.get("random_gen2"), apps.get("random_sum")
            if g1 and g2 and summ:
                self.flow_manager.add_flow_queue(None, net, service_key, summ["host"], g1["host"], TCP, None, g1["listen_port"])
                self.flow_manager.add_flow_queue(None, net, service_key, summ["host"], g2["host"], TCP, None, g2["listen_port"])
                self._restart_app(summ, self.service_definitions["random"][2][1], {"GEN1_IP": g1["ip"], "GEN2_IP": g2["ip"], "SERVICE_KEY": service_key})
        elif service_key.startswith("datetime"):
            date, timef, comb = apps.get("date_fetcher"), apps.get("time_fetcher"), apps.get("datetime_combiner")
            if date and timef and comb:
                self.flow_manager.add_flow_queue(None, net, service_key, comb["host"], date["host"], TCP, None, date["listen_port"])
                self.flow_manager.add_flow_queue(None, net, service_key, comb["host"], timef["host"], TCP, None, timef["listen_port"])
                self._restart_app(comb, self.service_definitions["datetime"][2][1], {"DATE_IP": date["ip"], "TIME_IP": timef["ip"], "SERVICE_KEY": service_key})
        elif service_key.startswith("colab"):
            a, b = apps.get("colab_a"), apps.get("colab_b")
            if a and b:
                self.flow_manager.add_flow_queue(None, net, service_key, a["host"], b["host"], TCP, None, b["listen_port"])
                self._restart_app(a, self.service_definitions["colab"][0][1], {"COLAB_B_IP": b["ip"], "SERVICE_KEY": service_key})
                              
    def _update_controller_service_members(self):
        # This method is less critical for *flow installation* now,
        # but if your controller or GUI still relies on this mapping for other reasons, keep it.
        # The controller won't be reactively installing flows based on this.
        mapping = {}
        for (service_key, _), inst in self.service_instances.items():
            mapping.setdefault(service_key, []).append(inst["ip"])
        if self.controller:
            # If your Ryu controller still has update_service_members for logging or other (non-flow) logic,
            # you can keep this call. Otherwise, it can be removed.
            # For this proactive approach, the controller itself doesn't need to know service members for flow decisions.
            self.controller.update_service_members(mapping)

