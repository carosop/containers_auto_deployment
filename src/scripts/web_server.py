import requests
import sys
import time
import os
import random

# Define the port for the database service
DB_PORT = 81
# Get the IP address of the database server from environment variable
# This will be set by the ServiceManager when deploying the service
DB_IP = os.getenv('DB_IP')
# Get the service key to identify the output file
SERVICE_KEY = os.getenv('SERVICE_KEY', 'unknown')

# Ensure the /shared directory exists for output
os.makedirs('/shared', exist_ok=True)

def fetch_data_from_db(db_ip, item_id):
    """
    Fetches data from the database server.
    """
    url = f"http://{db_ip}:{DB_PORT}/{item_id}"
    try:
        # Make an HTTP GET request to the database server
        response = requests.get(url, timeout=5)
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        return response.text
    except requests.exceptions.RequestException as e:
        return f"Error fetching from DB ({db_ip}): {e}"

if __name__ == "__main__":
    # Ensure standard output is flushed immediately
    sys.stdout.flush() 
    print(f"Web server started. Attempting to connect to DB at {DB_IP}:{DB_PORT}")

    if not DB_IP:
        print("[ERROR] DB_IP environment variable not set. Exiting.")
        sys.exit(1)

    result_data = []
    item_id = str(random.randint(1, 4))
    # Give the database server some time to start up
    time.sleep(2)
    data = fetch_data_from_db(DB_IP, item_id)
    print(f"Fetched data (item {item_id}): {data}")
    result_data.append(f"Item {item_id}: {data}")

    # Write results to a file in the shared directory
    output_path = f'/shared/{SERVICE_KEY}.txt'
    with open(output_path, 'w') as f:
        f.write("\n".join(result_data))
    print(f"Web server results written to {output_path}")
