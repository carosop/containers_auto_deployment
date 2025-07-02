import time
import socket
import sys
from datetime import datetime

# port for the date fetcher
PORT = 5002
# Bind to 0.0.0.0
HOST = "0.0.0.0"

def fetch_date():
    """Returns the current date in YYYY-MM-DD format."""
    return datetime.now().strftime('%Y-%m-%d')

if __name__ == "__main__":
    # Ensure standard output is flushed immediately
    sys.stdout.flush() 
    print(f"Date Fetcher started. Listening on {HOST}:{PORT}")

    # Create a TCP/IP socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # Allow reuse of address
        s.bind((HOST, PORT))
        s.listen()

        while True:
            conn, addr = s.accept()
            with conn:
                print(f"Connected by {addr} on port {PORT}")
                date_str = fetch_date()
                conn.sendall(date_str.encode())
                print(f"Sent date: {date_str}")
            time.sleep(1)
