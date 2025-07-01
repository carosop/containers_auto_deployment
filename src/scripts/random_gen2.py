import random
import time
import os
import socket
import sys

# Define the port for this generator (different from random_gen1 if on same host)
PORT = 5001 
# Bind to 0.0.0.0 to be accessible from any IP address on the host
HOST = "0.0.0.0"

def generate_random():
    """Generates a random integer between 1 and 100."""
    return str(random.randint(1, 100))

if __name__ == "__main__":
    # Ensure standard output is flushed immediately
    sys.stdout.flush() 
    print(f"Random Generator 2 started. Listening on {HOST}:{PORT}")

    # Create a TCP/IP socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # Allow reuse of address
        s.bind((HOST, PORT)) # Bind the socket to the host and port
        s.listen() # Listen for incoming connections

        while True:
            conn, addr = s.accept() # Accept a new connection
            with conn:
                print(f"Connected by {addr} on port {PORT}")
                random_num = generate_random()
                conn.sendall(random_num.encode()) # Send the random number
                print(f"Sent {random_num}")
            # Add a small delay
            time.sleep(1)
