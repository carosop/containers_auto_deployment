import time
import os
import socket

os.makedirs('/shared', exist_ok=True)
service_key = os.getenv('SERVICE_KEY', 'unknown')
time.sleep(5)

def wait_for_socket(socket_path, timeout=60):
    start_time = time.time()
    while not os.path.exists(socket_path):
        if time.time() - start_time > timeout:
            raise TimeoutError(f"Timeout waiting for socket {socket_path}")
        time.sleep(1)

def get_data(socket_path):
    wait_for_socket(socket_path)
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.connect(socket_path)
        return s.recv(1024).decode()

date_socket_path = "/shared/date_fetcher.sock"
time_socket_path = "/shared/time_fetcher.sock"

date = get_data(date_socket_path)
time = get_data(time_socket_path)
result = f'{date} {time}'

with open(f'/shared/{service_key}.txt', 'w') as f:
    f.write(result)
