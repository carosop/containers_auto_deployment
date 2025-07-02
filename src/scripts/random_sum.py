import os
import socket
import sys

# ports for the random generators
GEN1_PORT = 5000
GEN2_PORT = 5001

# Get IP addresses from environment variables
GEN1_IP = os.getenv('GEN1_IP')
GEN2_IP = os.getenv('GEN2_IP')
SERVICE_KEY = os.getenv('SERVICE_KEY', 'unknown')

# Ensure the /shared directory exists for output
os.makedirs('/shared', exist_ok=True)

def get_data_from_generator(gen_ip, gen_port):
    """
    Connects to a random generator and fetches a number.
    """
    if not gen_ip:
        return None, f"Generator IP not set for port {gen_port}"

    try:
        # Create a TCP/IP socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(10) # Set a timeout for connection and receive
            s.connect((gen_ip, gen_port)) # Connect to the generator
            data = s.recv(1024).decode() # Receive data
            print(f"Received {data} from {gen_ip}:{gen_port}")
            return int(data), None
    except socket.error as e:
        return None, f"Socket error with {gen_ip}:{gen_port}: {e}"
    except ValueError:
        return None, f"Invalid data from {gen_ip}:{gen_port}"
    except Exception as e:
        return None, f"An error occurred with {gen_ip}:{gen_port}: {e}"

if __name__ == "__main__":
    # Ensure standard output is flushed immediately
    sys.stdout.flush() 
    print(f"Random Sum started. Waiting for data from {GEN1_IP}:{GEN1_PORT} and {GEN2_IP}:{GEN2_PORT}")

    if not GEN1_IP or not GEN2_IP:
        print("[ERROR] One or both generator IPs not set. Exiting.")
        sys.exit(1)

    num1, err1 = get_data_from_generator(GEN1_IP, GEN1_PORT)
    num2, err2 = get_data_from_generator(GEN2_IP, GEN2_PORT)

    result_str = ""
    if num1 is not None and num2 is not None:
        total_sum = num1 + num2
        result_str = f"Sum of {num1} and {num2} is: {total_sum}"
        print(result_str)
    else:
        result_str = f"Failed to get numbers. Errors: Gen1: {err1}, Gen2: {err2}"
        print(result_str)

    # Write results to a file in the shared directory
    output_path = f'/shared/{SERVICE_KEY}.txt'
    with open(output_path, 'w') as f:
        f.write(result_str)
    print(f"Random Sum results written to {output_path}")
