# Network Deployment GUI

This project provides a graphical user interface (GUI) for deploying and managing network services using Docker containers and Mininet. It allows users to configure communication flows between services and manage their deployment on specified hosts.

## Project Structure

```
containers_auto_deployment
├── src
│   ├── main.py          # Entry point of the application
│   ├── gui.py           # GUI for service deployment
│   ├── network.py       # Network topologies and controller
│   └── services.py      # Service deployment and flow management
├── requirements.txt      # Project dependencies
├── Dockerfile            # Instructions for building the Docker image
└── README.md             # Project documentation
```

## Setup Instructions

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd containers_auto_deployment
   ```

2. **Install dependencies:**
   Ensure you have Python and pip installed, then run:
   ```bash
   pip install -r requirements.txt
   ```

3. **Build the Docker image:**
   ```bash
   docker build -t auto_deployment .
   ```

4. **Run the application:**
   Execute the main script:
   ```bash
   sudo python3 src/main.py
   ```