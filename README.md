# Containers auto deployment

This project automates the deployment and management of Docker services on an SDN network using Mininet and a Ryu controller. 
It supports two network topologies: a simple topology with four switches and six Docker hosts, and a complex topology with six switches and eight Docker hosts. 
The project includes a GUI for deploying, stopping and testing services, and automatically configures SDN flows for communication between services.

## Project Structure

```
containers_auto_deployment
├── src
│   ├── scripts
│   │   ├── web_server.py
│   │   ├── random_gen1.py
│   │   ├── random_gen2.py
│   │   ├── random_sum.py
│   │   ├── date_fetcher.py
│   │   ├── time_fetcher.py
│   │   ├── database.py
│   │   └── datetime_combiner.py
│   ├── main.py
│   ├── gui.py
│   ├── network.py
│   └── services.py
├── requirements.txt
├── Dockerfile
└── README.md
```

## Setup Instructions

1. **Install Comnetsemu (preferably using Vagrant)** 
   This project is designed to work within the Comnetsemu environment.
      You can find the installation instructions here:
      https://git.comnets.net/public-repo/comnetsemu#installation

      For additional information, refer to:
      https://www.granelli-lab.org/researches/relevant-projects/comnetsemu-labs

2. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd containers_auto_deployment
   ```

3. **Check the Comnetsemu version**
   This project was developed on Ubuntu 20.04 with Comnetsemu (ubuntu-20.04-comnetsemu). 
   Ensure that the Ryu controller is located at:
      ```bash
      /usr/lib/python3/dist-packages/ryu/app/simple_switch_stp_13.py
      ```
      Verify the *path* variable in the `network.py` file:
      ```bash
      cd src
      nano network.py
      ```
      If necessary, update the *path* variable in the **start_ryu_controller** function to match your Ryu controller location:
      ```python
      def start_ryu_controller():
          """
          Start the Ryu controller.
          """
          path = "/path/to/your/ryu/controller/simple_switch_stp_13.py"
          ...
      ```

4. **Build the Docker image:**
   ```bash
   docker build -t auto_deployment .
   ```

5. **Run the application:**
   Execute the main script:
   ```bash
   sudo python3 src/main.py
   ```