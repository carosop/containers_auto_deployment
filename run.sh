#!/bin/bash

set -e

# Cleanup any previous Mininet state
sudo mn -c

# Start Ryu controller in the background
echo "Starting Ryu controller..."
ryu-manager --ofp-tcp-listen-port 6653 --verbose src/controller.py ryu.app.rest_conf_switch ryu.app.ofctl_rest > ryu.log 2>&1 &
RYU_PID=$!

# Wait for Ryu REST API to be up
echo "Waiting for Ryu REST API to be up..."
for i in {1..30}; do
    if curl -s http://localhost:8080/stats/switches >/dev/null; then
        echo "Ryu REST API is up."
        break
    fi
    if ! kill -0 $RYU_PID 2>/dev/null; then
        echo "Ryu controller failed to start. Check ryu.log."
        exit 1
    fi
    sleep 1
    if [ $i -eq 30 ]; then
        echo "Ryu REST API did not start in time. Check ryu.log."
        kill $RYU_PID
        exit 1
    fi
done

# Wait for Ryu to listen on OpenFlow port 6653
echo "Waiting for Ryu to listen on TCP port 6653..."
for i in {1..30}; do
    if netstat -lnt | grep -q ':6653'; then
        echo "Ryu is listening on port 6653."
        break
    fi
    if ! kill -0 $RYU_PID 2>/dev/null; then
        echo "Ryu controller failed to start. Check ryu.log."
        exit 1
    fi
    sleep 1
    if [ $i -eq 30 ]; then
        echo "Ryu did not listen on port 6653 in time. Check ryu.log."
        kill $RYU_PID
        exit 1
    fi
done

# Start your main application
echo "Starting main application..."
sudo -E python3 src/main.py

# When done, kill Ryu
echo "Shutting down Ryu controller..."
kill $RYU_PID