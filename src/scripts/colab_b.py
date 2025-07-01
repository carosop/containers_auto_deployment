import socket
import sys
import os
import time

# Define the port for colab_b to listen on
PORT = 5004
# Bind to 0.0.0.0
HOST = "0.0.0.0"

if __name__ == "__main__":
    # Ensure standard output is flushed immediately
    sys.stdout.flush()
    print(f"Colab B server started. Listening on {HOST}:{PORT}")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # Allow reuse of address
        s.bind((HOST, PORT))
        s.listen()

        while True:
            conn, addr = s.accept()
            with conn:
                print(f"Connected by {addr} on port {PORT}")
                data = conn.recv(1024).decode()
                print(f"Colab B received: {data}")
                response = f"Colab B received your message: '{data}'"
                conn.sendall(response.encode())
                print(f"Colab B sent: {response}")
            time.sleep(1)
