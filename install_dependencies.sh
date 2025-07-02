#!/bin/bash

set -e

echo "--- Starting dependency installation script ---"

# --- 1. Update system package lists ---
echo "Updating system package lists..."
sudo apt-get update -y
echo "System package lists updated."

# --- 2. Install system-level dependencies ---
echo "Installing system-level dependencies: mininet, openvswitch-switch, python3-pip, python3-tk..."
# Install Mininet, Open vSwitch, Python 3 pip and Tkinter for GUI support
sudo apt-get install -y mininet openvswitch-switch python3-pip python3-tk
echo "System-level dependencies installed."

# --- 3. Install Python dependencies using pip3 ---
echo "Installing Python packages using pip3..."
pip3 install ryu networkx requests
echo "Python packages installed."

echo "--- Dependency installation complete! ---"
echo ""
echo "NEXT STEPS TO RUN YOUR APPLICATION:"
echo "1. If you are running on a remote server, ensure X11 forwarding is set up (ssh -X or ssh -Y)."
echo "   On the remote server, check /etc/ssh/sshd_config for 'X11Forwarding yes' and restart sshd if needed."
echo "2. Run the application using the provided script:"
echo "   ./run_unix.sh"
echo "   or for Windows:"
echo "   ./run_windows.sh"
echo "3. Ensure you have the necessary permissions to run the scripts."
echo "   If you encounter permission issues, run:"     
echo "   chmod +x run_unix.sh"
echo "   or for Windows:"
echo "   chmod +x run_windows.sh"
echo ""
echo "Enjoy your Container auto deployment run!"