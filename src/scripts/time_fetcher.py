import time
import os
import socket
import sys
from datetime import datetime

# Define the port for the time fetcher
PORT = 5003
# Bind to 0.0.0.0
HOST = "0.0.0.0"

def fetch_time():
    """Returns the current time in HH:MM:SS format."""
    return datetime.now().strftime('%H:%M:%S')

if __name__ == "__main__":
    # Ensure standard output is flushed immediately
    sys.stdout.flush() 
    print(f"Time Fetcher started. Listening on {HOST}:{PORT}")

    # Create a TCP/IP socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # Allow reuse of address
        s.bind((HOST, PORT))
        s.listen()

        while True:
            conn, addr = s.accept()
            with conn:
                print(f"Connected by {addr} on port {PORT}")
                time_str = fetch_time()
                conn.sendall(time_str.encode())
                print(f"Sent time: {time_str}")
            time.sleep(1)
