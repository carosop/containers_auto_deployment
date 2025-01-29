import tkinter as tk
from tkinter import ttk
from services import deploy_service, stop_service, setup_flow, remove_flow, flows

class ServiceDeployGUI:
    def __init__(self, root, mgr, net):
        self.root = root
        self.mgr = mgr
        self.net = net
        self.services = ["webserver", "database"]  # Example services
        self.setup_gui()

    def setup_gui(self):
        self.root.title("SDN Service Deployment")
        frame = ttk.LabelFrame(self.root, text="Service Deployment")
        frame.grid(row=0, column=0, padx=10, pady=10)

        ttk.Label(frame, text="Service Name:").grid(row=0, column=0)
        self.service_combobox = ttk.Combobox(frame, values=self.services)
        self.service_combobox.grid(row=0, column=1)

        ttk.Label(frame, text="Host:").grid(row=1, column=0)
        self.host_combobox = ttk.Combobox(frame, values=[host.name for host in self.net.hosts])
        self.host_combobox.grid(row=1, column=1)

        ttk.Button(frame, text="Deploy", command=self.deploy_service_callback).grid(row=2, column=0)

        # Active Services Section
        active_services_frame = ttk.LabelFrame(self.root, text="Active Services")
        active_services_frame.grid(row=1, column=0, padx=10, pady=10)

        self.active_services_listbox = tk.Listbox(active_services_frame)
        self.active_services_listbox.grid(row=0, column=0)

        ttk.Button(active_services_frame, text="Stop", command=self.stop_selected_service).grid(row=1, column=0)

        # Communication Requirements Section
        comm_frame = ttk.LabelFrame(self.root, text="Communication Requirements")
        comm_frame.grid(row=2, column=0, padx=10, pady=10)

        ttk.Label(comm_frame, text="Source Service:").grid(row=0, column=0)
        self.src_service_combobox = ttk.Combobox(comm_frame)
        self.src_service_combobox.grid(row=0, column=1)

        ttk.Label(comm_frame, text="Destination Service:").grid(row=1, column=0)
        self.dst_service_combobox = ttk.Combobox(comm_frame)
        self.dst_service_combobox.grid(row=1, column=1)

        ttk.Button(comm_frame, text="Set Flow", command=self.set_flow_callback).grid(row=2, column=0, columnspan=2)

        # Active Flows Section
        flow_frame = ttk.LabelFrame(self.root, text="Active Flows")
        flow_frame.grid(row=3, column=0, padx=10, pady=10)

        self.flow_listbox = tk.Listbox(flow_frame)
        self.flow_listbox.grid(row=0, column=0)

        self.update_service_combobox()
        self.update_active_services_listbox()

    def update_service_combobox(self):
        services = []
        for host in self.net.hosts:
            services.extend(self.mgr.getContainersDhost(host.name))
        self.src_service_combobox['values'] = services
        self.src_service_combobox.set('') 
        self.dst_service_combobox['values'] = services
        self.dst_service_combobox.set('') 

    def update_active_services_listbox(self):
        self.active_services_listbox.delete(0, tk.END)
        services = []
        for host in self.net.hosts:
            services.extend(self.mgr.getContainersDhost(host.name))
        for service in services:
            self.active_services_listbox.insert(tk.END, service)

    def deploy_service_callback(self):
        service_name = self.service_combobox.get()
        host = self.host_combobox.get()
        if not service_name:
            print("[ERROR] Service name is required.")
            return
        if service_name == "webserver":
            deploy_service(self.mgr, service_name, "httpd:alpine", "httpd-foreground", host)
        elif service_name == "database":
            deploy_service(self.mgr, service_name, "mysql:latest", "mysqld", host)
        self.update_service_combobox()
        self.update_active_services_listbox()
        self.update_flow_listbox()

    def stop_selected_service(self):
        selected_service = self.active_services_listbox.get(tk.ACTIVE)
        if not selected_service:
            print("[ERROR] No service selected.")
            return
        stop_service(self.mgr, selected_service)
        
        try:
            src_host = selected_service.split('_')[1]
            src_ip = self.net.get(src_host).IP()
            switch = self.get_switch_for_host(src_host)
            # Remove flows associated with the service
            for flow in list(flows.keys()):
                if src_ip in flow:
                    remove_flow(switch, flow[0], flow[1])
        except IndexError:
            print("[ERROR] Service names must be in the format 'service_host'.")
        except KeyError as e:
            print(f"[ERROR] Invalid source host: {e}")
        except AttributeError as e:
            print(f"[ERROR] Failed to get switch for host: {e}")

        self.update_service_combobox()
        self.update_active_services_listbox()
        self.update_flow_listbox()
        
    def get_switch_for_host(self, host):
        """
        Get the switch associated with a given host by checking the links.
        """
        for link in self.net.links:
            if host in link.intf1.node.name:
                return link.intf2.node
            elif host in link.intf2.node.name:
                return link.intf1.node
        return None

    def set_flow_callback(self):
        src_service = self.src_service_combobox.get()
        dst_service = self.dst_service_combobox.get()
        if not src_service or not dst_service:
            print("[ERROR] Both source and destination services are required.")
            return

        # Extract the hostnames from the service names
        try:
            src_host = src_service.split('_')[1]
            dst_host = dst_service.split('_')[1]
        except IndexError:
            print("[ERROR] Service names must be in the format 'service_host'.")
            return

        # Get the IP addresses of the hosts dynamically
        try:
            src_ip = self.net.get(src_host).IP()
            dst_ip = self.net.get(dst_host).IP()
        except KeyError as e:
            print(f"[ERROR] Invalid source or destination host: {e}")
            return

        # Determine the switch and ports based on the hosts
        if src_host in ["h1"] and dst_host in ["h1"]:
            s1 = self.net.get('s1')
            setup_flow(s1, src_ip, dst_ip, 1, 2)
        elif src_host in ["h2", "h3"] and dst_host in ["h2", "h3"]:
            s2 = self.net.get('s2')
            setup_flow(s2, src_ip, dst_ip, 1, 2)
        elif src_host in ["h4"] and dst_host in ["h4"]:
            s3 = self.net.get('s3')
            setup_flow(s3, src_ip, dst_ip, 1, 2)
        elif src_host in ["h5", "h6"] and dst_host in ["h5", "h6"]:
            s4 = self.net.get('s4')
            setup_flow(s4, src_ip, dst_ip, 1, 2)
        else:
            # Handle inter-switch flows
            if src_host in ["h1"] and dst_host in ["h2", "h3"]:
                s1 = self.net.get('s1')
                s2 = self.net.get('s2')
                setup_flow(s1, src_ip, "10.0.0.2", 1, 2)  # Example intermediate IP
                setup_flow(s2, "10.0.0.2", dst_ip, 1, 2)
            elif src_host in ["h2", "h3"] and dst_host in ["h4"]:
                s2 = self.net.get('s2')
                s3 = self.net.get('s3')
                setup_flow(s2, src_ip, "10.0.0.4", 1, 2)  # Example intermediate IP
                setup_flow(s3, "10.0.0.4", dst_ip, 1, 2)
            elif src_host in ["h4"] and dst_host in ["h5", "h6"]:
                s3 = self.net.get('s3')
                s4 = self.net.get('s4')
                setup_flow(s3, src_ip, "10.0.0.5", 1, 2)  # Example intermediate IP
                setup_flow(s4, "10.0.0.5", dst_ip, 1, 2)
            elif src_host in ["h1"] and dst_host in ["h5", "h6"]:
                s1 = self.net.get('s1')
                s4 = self.net.get('s4')
                setup_flow(s1, src_ip, "10.0.0.5", 1, 2)  # Example intermediate IP
                setup_flow(s4, "10.0.0.5", dst_ip, 1, 2)

        self.update_flow_listbox()

    def update_flow_listbox(self):
        self.flow_listbox.delete(0, tk.END)
        for flow in flows.keys():
            self.flow_listbox.insert(tk.END, f"{flow[0]} -> {flow[1]}")