import socket
import time
import os

os.makedirs('/shared', exist_ok=True)
service_key = os.getenv('SERVICE_KEY', 'unknown')
time.sleep(5)

def wait_for_socket(socket_path, timeout=60):
    start_time = time.time()
    while not os.path.exists(socket_path):
        if time.time() - start_time > timeout:
            raise TimeoutError(f"Timeout waiting for socket {socket_path}")
        time.sleep(1)

def get_random_number(socket_path):
    wait_for_socket(socket_path)
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.connect(socket_path)
        return int(s.recv(1024).decode())

a = get_random_number("/shared/random_gen1.sock")
b = get_random_number("/shared/random_gen2.sock")
result = f'{a} + {b} = {a+b}'

with open(f'/shared/{service_key}.txt', 'w') as f:
    f.write(result)
