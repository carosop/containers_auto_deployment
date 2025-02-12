import random
import time
import os
import socket

def generate_random():
    return str(random.randint(1, 100))

if __name__ == "__main__":
    socket_path = "/shared/random_gen2.sock"
    if os.path.exists(socket_path):
        os.remove(socket_path)
    os.makedirs(os.path.dirname(socket_path), exist_ok=True)
    time.sleep(5)
    
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.bind(socket_path)
        s.listen()
        while True:
            conn, addr = s.accept()
            with conn:
                conn.sendall(generate_random().encode())
