# Containers Auto Deployment

This project automates the deployment and management of services on an SDN network using Mininet and a Ryu controller. <br />
It supports two network topologies: a simple topology with four switches and six hosts and a complex topology with seven switches and nineteen hosts. <br />
The project includes a GUI for deploying, stopping, and testing services, and automatically configures SDN flows for communication between services.

---

## Project Structure

```
containers_auto_deployment
├── src
│   ├── scripts                     # Service scripts
│   │   ├── colab_a.py             
│   │   ├── colab_b.py              
│   │   ├── database.py             
│   │   ├── date_fetcher.py         
│   │   ├── datetime_combiner.py    
│   │   ├── random_gen1.py          
│   │   ├── random_gen2.py          
│   │   ├── random_sum.py           
│   │   ├── time_fetcher.py         
│   │   └── web_server.py           
│   ├── main.py                     # Application entry point
│   ├── gui.py                      # GUI logic
│   ├── network.py                  # Topology management
│   ├── services.py                 # Service deployment logic
│   ├── flow.py                     # SDN flow manager
│   └── controller.py               # Ryu SDN controller
├── install_dependencies.sh         # Dependency installer script
├── run_unix.sh                     # Run script (Unix)
├── run_windows.sh                  # Run script (Windows)
└── README.md                       
```
---

## Setup Instructions

### 1. **Install Comnetsemu (preferably using Vagrant):**

This project is designed to work within the Comnetsemu environment.  
You can find the installation instructions here:  
https://git.comnets.net/public-repo/comnetsemu#installation

For additional information, refer to:  
https://www.granelli-lab.org/researches/relevant-projects/comnetsemu-labs

---

### 2. **Clone the repository inside comnetsemu:**

```bash
git clone https://github.com/carosop/containers_auto_deployment.git
cd containers_auto_deployment
```

---

### 3. **Install dependencies:**

Use the provided script to install all required system and Python packages:

```bash
chmod +x install_dependencies.sh
./install_dependencies.sh
```

---

### 4. **Run the application:**

#### **Recommended: Use the provided run script**

For Unix/Linux:
```bash
chmod +x run_unix.sh
./run_unix.sh
```

For Windows (WSL/Mininet VM):
```bash
chmod +x run_windows.sh
./run_windows.sh
```

These scripts will:
- Clean up any previous Mininet state
- Start the Ryu controller (with REST API and your custom controller)
- Wait for Ryu to be ready
- Start the main application (with GUI)
- Clean up on exit

#### **Manual Run:**

1. **Start the Ryu controller (with REST API):**
   ```bash
   ryu-manager --ofp-tcp-listen-port 6653 --verbose src/controller.py ryu.app.ofctl_rest > ryu.log 2>&1 &
   ```

2. **Start the main application:**
   ```bash
   sudo python3 src/main.py
   ```

---

## Usage

- On startup, select the topology type (simple or complex).
- The GUI will launch automatically.
- Use the GUI to deploy, stop, and test services.
- The system will automatically manage SDN flows for service communication.
- Service results and logs are written to `/shared` on each host.

---

## Notes

- The Ryu controller is **internal** to this project: see [`src/controller.py`](src/controller.py).
- The REST API (`ryu.app.ofctl_rest`) is required for dynamic flow management.
- All service scripts are copied to each Mininet host under `/shared/scripts/`.
- The `/shared` directory is used for inter-process communication and result files.
- The GUI uses Tkinter; ensure you have X11 forwarding enabled if running remotely.

---

## Troubleshooting
- If the GUI does not appear, check your X11 forwarding settings.
- If services fail to deploy, check that all dependencies are installed and that `/shared/scripts/` exists on each host.
- For controller or flow issues, check `ryu.log` for errors.

