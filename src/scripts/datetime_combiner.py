import os
import socket
import sys

# ports for date and time fetchers
DATE_PORT = 5002
TIME_PORT = 5003

# IP addresses from environment variables
DATE_IP = os.getenv('DATE_IP')
TIME_IP = os.getenv('TIME_IP')
SERVICE_KEY = os.getenv('SERVICE_KEY', 'unknown')

# Ensure the /shared directory exists for output
os.makedirs('/shared', exist_ok=True)

def get_data_from_fetcher(fetcher_ip, fetcher_port):
    """
    Connects to a date/time fetcher and retrieves data.
    """
    if not fetcher_ip:
        return None, f"Fetcher IP not set for port {fetcher_port}"
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(10) # Set a timeout
            s.connect((fetcher_ip, fetcher_port))
            data = s.recv(1024).decode()
            print(f"Received {data} from {fetcher_ip}:{fetcher_port}")
            return data, None
    except socket.error as e:
        return None, f"Socket error with {fetcher_ip}:{fetcher_port}: {e}"
    except Exception as e:
        return None, f"An error occurred with {fetcher_ip}:{fetcher_port}: {e}"

if __name__ == "__main__":
    # Ensure standard output is flushed immediately
    sys.stdout.flush() 
    print(f"Datetime Combiner started. Waiting for data from {DATE_IP}:{DATE_PORT} and {TIME_IP}:{TIME_PORT}")

    if not DATE_IP or not TIME_IP:
        print("[ERROR] One or both fetcher IPs not set. Exiting.")
        sys.exit(1)

    date_data, err_date = get_data_from_fetcher(DATE_IP, DATE_PORT)
    time_data, err_time = get_data_from_fetcher(TIME_IP, TIME_PORT)

    result_str = ""
    if date_data and time_data:
        result_str = f"Combined Datetime: {date_data} {time_data}"
        print(result_str)
    else:
        result_str = f"Failed to get date/time. Errors: Date: {err_date}, Time: {err_time}"
        print(result_str)

    # Write results to a file in the shared directory
    output_path = f'/shared/{SERVICE_KEY}.txt'
    with open(output_path, 'w') as f:
        f.write(result_str)
    print(f"Datetime Combiner results written to {output_path}")
