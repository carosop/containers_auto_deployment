#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

echo "--- Starting dependency installation script ---"

# --- 1. Update system package lists ---
echo "Updating system package lists..."
sudo apt-get update -y
echo "System package lists updated."

# --- 2. Install system-level dependencies ---
echo "Installing system-level dependencies: mininet, openvswitch-switch, python3-pip, python3-tk..."
# Install Mininet, Open vSwitch, Python 3 pip, and Tkinter for GUI support
sudo apt-get install -y mininet openvswitch-switch python3-pip python3-tk
echo "System-level dependencies installed."

# --- 3. Install Python dependencies using pip3 ---
echo "Installing Python packages using pip3..."
# Install ryu, networkx, and requests globally for system Python 3
pip3 install ryu networkx requests
echo "Python packages installed."

echo "--- Dependency installation complete! ---"
echo ""
echo "NEXT STEPS TO RUN YOUR APPLICATION:"
echo "1. If you are running on a remote server, ensure X11 forwarding is set up (ssh -X or ssh -Y)."
echo "   On the remote server, check /etc/ssh/sshd_config for 'X11Forwarding yes' and restart sshd if needed."
echo "2. Navigate to your project directory (where main.py is located)."
echo "   e.g., cd /home/vagrant/comnetsemu/containers_auto_deployment/src"
echo "3. Run your main application script using 'sudo -E' to preserve environment variables for GUI:"
echo "   sudo -E python3 main.py"
echo ""
echo "Enjoy your Container auto deployment run!"
# --- End of script ---