import socket
import sys
import os

COLAB_B_PORT = 5004
# IP address from environment variable
COLAB_B_IP = os.getenv('COLAB_B_IP')
SERVICE_KEY = os.getenv('SERVICE_KEY', 'unknown')

# Ensure the /shared directory exists for output
os.makedirs('/shared', exist_ok=True)

if __name__ == "__main__":
    # Ensure standard output is flushed immediately
    sys.stdout.flush()
    print(f"Colab A client started. Attempting to connect to Colab B at {COLAB_B_IP}:{COLAB_B_PORT}")

    if not COLAB_B_IP:
        print("[ERROR] COLAB_B_IP environment variable not set. Exiting.")
        sys.exit(1)

    result_str = ""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(10)
            s.connect((COLAB_B_IP, COLAB_B_PORT))
            message = "Hello from Colab A!"
            s.sendall(message.encode())
            print(f"Sent: {message}")
            
            data = s.recv(1024).decode()
            result_str = f"Colab A received: {data}"
            print(result_str)

    except socket.error as e:
        result_str = f"Colab A socket error: {e}"
        print(result_str)
    except Exception as e:
        result_str = f"Colab A error: {e}"
        print(result_str)
    
    # Write results to a file
    output_path = f'/shared/{SERVICE_KEY}.txt'
    with open(output_path, 'w') as f:
        f.write(result_str)
    print(f"Colab A results written to {output_path}")
