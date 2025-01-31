import tkinter as tk
from tkinter import ttk
from services import deploy_service, stop_service, flows

class ServiceDeployGUI:
    def __init__(self, root, mgr, net):
        self.root = root
        self.mgr = mgr
        self.net = net
        self.services = ["web", "cache", "monitoring", "logging", "messaging", "analytics"]  # Example services
        self.setup_gui()

    def setup_gui(self):
        self.root.title("SDN Service Deployment")
        frame = ttk.LabelFrame(self.root, text="Service Deployment")
        frame.grid(row=0, column=0, padx=10, pady=10)

        ttk.Label(frame, text="Service Type:").grid(row=0, column=0)
        self.service_combobox = ttk.Combobox(frame, values=self.services)
        self.service_combobox.grid(row=0, column=1)

        ttk.Button(frame, text="Deploy", command=self.deploy_service_callback).grid(row=1, column=0)

        # Active Services Section
        active_services_frame = ttk.LabelFrame(self.root, text="Active Services")
        active_services_frame.grid(row=1, column=0, padx=10, pady=10)

        self.active_services_listbox = tk.Listbox(active_services_frame)
        self.active_services_listbox.grid(row=0, column=0)

        ttk.Button(active_services_frame, text="Stop", command=self.stop_selected_service).grid(row=1, column=0)

        self.update_active_services_listbox()

    def update_active_services_listbox(self):
        self.active_services_listbox.delete(0, tk.END)
        services = []
        for host in self.net.hosts:
            services.extend(self.mgr.getContainersDhost(host.name))
        for service in services:
            self.active_services_listbox.insert(tk.END, service)

    def deploy_service_callback(self):
        service_name = self.service_combobox.get()
        if not service_name:
            print("[ERROR] Service name is required.")
            return
        deploy_service(self.mgr, service_name, self.net)
        self.update_active_services_listbox()

    def stop_selected_service(self):
        selected_service = self.active_services_listbox.get(tk.ACTIVE)
        if not selected_service:
            print("[ERROR] No service selected.")
            return
        stop_service(self.mgr, selected_service)
        self.update_active_services_listbox()
