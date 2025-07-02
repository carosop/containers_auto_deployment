import tkinter as tk
from tkinter import ttk
from services import ServiceManager

class ServiceDeployGUI:
    def __init__(self, root, net, flow_queue):
        self.root = root
        self.net = net
        self.service_manager = ServiceManager()
        self.service_manager.flow_modification_queue = flow_queue

        self.services = ["web", "random", "datetime"]
        
        # init gui with colab services and update
        self.setup_gui()

        # Deploy colab service on all hosts at GUI startup
        self.service_manager.deploy_colab_on_all_hosts(self.net)

        self.update_communication_results()
        self.update_active_services()
        self.update_test_service_combobox()
        
    
    def update_test_service_combobox(self):
        active_service = sorted({s_k for (s_k, _) in self.service_manager.service_instances})
        self.test_service_combobox["values"] = active_service
        if active_service:
            self.test_service_combobox.set(active_service[0])
    
    def setup_gui(self):
        self.root.title("SDN Service Deployment & Monitoring")
        self.root.minsize(1200, 600)  
        for i in range(2):
            self.root.grid_rowconfigure(i, weight=1)
            self.root.grid_columnconfigure(i, weight=1)

        # Service Deployment
        deploy_frame = ttk.LabelFrame(self.root, text="Service Deployment")
        deploy_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        deploy_frame.grid_rowconfigure(0, weight=1)
        deploy_frame.grid_columnconfigure(1, weight=1)
        ttk.Label(deploy_frame, text="Service Type:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.service_combobox = ttk.Combobox(deploy_frame, values=self.services, state="readonly")
        self.service_combobox.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.service_combobox.set("web")
        ttk.Button(deploy_frame, text="Deploy", command=self.deploy_service_callback).grid(row=1, column=0, columnspan=2, pady=10)

        # Active Services
        active_frame = ttk.LabelFrame(self.root, text="Active Services")
        active_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        active_frame.grid_rowconfigure(0, weight=1)
        active_frame.grid_columnconfigure(0, weight=1)
        self.active_services_listbox = tk.Listbox(active_frame, height=10, width=40)
        self.active_services_listbox.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        ttk.Button(active_frame, text="Stop Selected", command=self.stop_selected_service).grid(row=1, column=0, pady=5)
        ttk.Button(active_frame, text="Refresh", command=self.update_active_services).grid(row=2, column=0, pady=5)

        # Communication Flows
        flow_frame = ttk.LabelFrame(self.root, text="SDN Communication Flows")
        flow_frame.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")
        flow_frame.grid_rowconfigure(0, weight=1)
        flow_frame.grid_columnconfigure(0, weight=1)
        self.communication_results_text = tk.Text(flow_frame, height=15, width=60, state="disabled")
        self.communication_results_text.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        ttk.Button(flow_frame, text="Refresh Flows", command=self.update_communication_results).grid(row=1, column=0, pady=5)

        # Test Results
        test_frame = ttk.LabelFrame(self.root, text="Service Test Results")
        test_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        flow_frame.grid_rowconfigure(0, weight=1)
        flow_frame.grid_columnconfigure(0, weight=1)
        ttk.Label(test_frame, text="Service to Test:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.test_service_combobox = ttk.Combobox(test_frame, values=self.services, state="readonly")
        self.test_service_combobox.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.test_service_combobox.set("web")
        self.test_results_text = tk.Text(test_frame, height=10, width=60, state="disabled")
        self.test_results_text.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky="nsew")
        ttk.Button(test_frame, text="Test", command=self.test_selected_service).grid(row=2, column=0, columnspan=2, pady=5)

    def deploy_service_callback(self):
        service_name = self.service_combobox.get()
        if service_name:
            self.service_manager.control_services(self.net, action='deploy', service_name=service_name, gui=self)
            self.update_active_services()
            self.update_communication_results()
            self.update_test_service_combobox()

    def stop_selected_service(self):
        selected = self.active_services_listbox.curselection()
        if not selected:
            return
        selected_service = self.active_services_listbox.get(selected[0])
        parts = {p.split(': ')[0]: p.split(': ')[1] for p in selected_service.split(', ')}
        service_key = parts.get('Service')
        app_name = parts.get('App')
        if service_key and app_name:
            self.service_manager.control_services(self.net, action='stop', service_name=service_key, selected_process=selected_service, gui=self)
            self.update_active_services()
            self.update_communication_results()
            self.update_test_service_combobox()
            # Try redeploy colab
            self.service_manager.try_redeploy_colab(self.net)

    def update_active_services(self):
        self.active_services_listbox.delete(0, tk.END)
        for service_info in self.service_manager.update_gui_with_active_services():
            self.active_services_listbox.insert(tk.END, service_info)

    def update_communication_results(self):
        self.communication_results_text.config(state="normal")
        self.communication_results_text.delete(1.0, tk.END)
        active_flows = self.service_manager.update_gui_with_active_flows()["flows"]
        if not active_flows:
            self.communication_results_text.insert(tk.END, "No active flows detected.\n")
        else:
            for (service_key, src_ip, dst_ip, dst_port, protocol, dpid, in_port), details in active_flows.items():
                out_port = details.get('out_port', 'N/A')
                priority = details.get('priority', 'N/A')
                flow_line = (f"Service: {service_key}, {src_ip} -> {dst_ip}, "
                             f"DPID: {dpid}, InPort: {in_port}, OutPort: {out_port}, "
                             f"Priority: {priority}, DstPort: {dst_port}, Proto: {protocol}\n")
                self.communication_results_text.insert(tk.END, flow_line)
        self.communication_results_text.config(state="disabled")

    def test_selected_service(self):
        service_to_test = self.test_service_combobox.get()
        self.test_results_text.config(state="normal")
        self.test_results_text.delete(1.0, tk.END)
        self.test_results_text.insert(tk.END, f"Running test for {service_to_test}...\n")
        self.root.update_idletasks()
        test_results = self.service_manager.test_service(service_to_test)
        self.test_results_text.delete(1.0, tk.END)
        if test_results:
            for service_key, result in test_results.items():
                self.test_results_text.insert(tk.END, f"Service: {service_key}\nResult:\n{result}\n\n")
        else:
            self.test_results_text.insert(tk.END, "No test results available.\n")
        self.test_results_text.config(state="disabled")