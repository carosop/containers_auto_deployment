import tkinter as tk
from tkinter import ttk
from services import control_services, update_gui_with_active_flows, test_services

class ServiceDeployGUI:
    def __init__(self, root, mgr, net):
        self.root = root
        self.mgr = mgr
        self.net = net
        # Example services names
        self.services = ["web", "random", "datetime"]  
        self.setup_gui()
        # Automatically update communication results when GUI is opened
        self.update_communication_results() 
        
    def setup_gui(self):
        self.root.title("SDN Service Deployment")
        frame = ttk.LabelFrame(self.root, text="Service Deployment")
        frame.grid(row=0, column=0, padx=10, pady=10)

        ttk.Label(frame, text="Service Type:").grid(row=0, column=0)
        self.service_combobox = ttk.Combobox(frame, values=self.services)
        self.service_combobox.grid(row=0, column=1)

        ttk.Button(frame, text="Deploy", command=self.deploy_service_callback).grid(row=1, column=0)

        # Active Services Section
        active_services_frame = ttk.LabelFrame(self.root, text="Active Processes")
        active_services_frame.grid(row=1, column=0, padx=10, pady=10)

        self.active_services_listbox = tk.Listbox(active_services_frame, height=12, width=30) 
        self.active_services_listbox.grid(row=0, column=0)

        ttk.Button(active_services_frame, text="Stop", command=self.stop_selected_service).grid(row=1, column=0)

        self.update_active_services_listbox()

        # Communication Results Section
        communication_results_frame = ttk.LabelFrame(self.root, text="Flows")
        communication_results_frame.grid(row=2, column=0, padx=10, pady=10)

        self.communication_results_text = tk.Text(communication_results_frame, height=20, width=70)
        self.communication_results_text.grid(row=0, column=0)

        # Service Test Results Section
        test_results_frame = ttk.LabelFrame(self.root, text="Service Test Results")
        test_results_frame.grid(row=0, column=1, rowspan=3, padx=10, pady=10)

        self.test_results_text = tk.Text(test_results_frame, height=30, width=70)
        self.test_results_text.grid(row=0, column=0)

        ttk.Button(test_results_frame, text="Test Services", command=self.test_services_callback).grid(row=1, column=0)

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
        control_services(self.mgr, self.net, action='deploy', service_name=service_name, gui=self)

    def stop_selected_service(self):
        selected_service = self.active_services_listbox.get(tk.ACTIVE)
        if not selected_service:
            print("[ERROR] No service selected.")
            return
        control_services(self.mgr, self.net, action='stop', selected_process=selected_service, gui=self)
    
    def update_communication_results(self):
        self.communication_results_text.delete(1.0, tk.END)
        active_flows = update_gui_with_active_flows()["flows"]
        for (key, src_ip, dst_ip), details in active_flows.items():
            self.communication_results_text.insert(tk.END, f"Service: {key}, Flow: {src_ip} -> {dst_ip}, Switch: {details['switch']}, In Port: {details['in_port']}, Out Port: {details['out_port']}\n")
            
    def update_test_results(self, test_results):
        self.test_results_text.delete(1.0, tk.END)
        for result in test_results:
            self.test_results_text.insert(tk.END, f"{result}\n")

    def test_services_callback(self):
        test_results = test_services(self.mgr, self.net, self)
        self.update_test_results(test_results)
