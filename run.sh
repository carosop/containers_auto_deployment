#!/bin/bash

# Start Ryu controller in the background
ryu-manager --ofp-tcp-listen-port 6653 --verbose src/controller.py ryu.app.rest_conf_switch ryu.app.ofctl_rest > ryu.log 2>&1 &
RYU_PID=$!

# Wait for Ryu REST API to be up
for i in {1..30}; do
    if curl -s http://localhost:8080/stats/switches >/dev/null; then
        echo "Ryu REST API is up."
        break
    fi
    sleep 1
done

# Start your main application
sudo -E python3 src/main.py

# When done, kill Ryu
kill $RYU_PID