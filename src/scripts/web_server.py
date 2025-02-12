import http.server
import socketserver
import os
import requests
import sys
import logging 
PORT = 80
host = os.getenv('HOSTNAME', '0.0.0.0')

# Configure logging
logging.basicConfig(level=logging.INFO)

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        item_id = self.path.strip("/")
        if not item_id:  # Root request
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'<html><body><h1>Web Server is running</h1></body></html>')
            return

        # Fetch data from the database server
        try:
            response = requests.get(f"{database_url}/{item_id}")
            item = response.text
        except requests.ConnectionError:
            item = "Database unavailable"

        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(item.encode())

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 web_server.py <database_url>")
        sys.exit(1)

    database_url = sys.argv[1]

    with socketserver.TCPServer((host, PORT), Handler) as httpd:
        logging.info(f"Serving on port {PORT}, host {host}")
        logging.info(f"Using database URL: {database_url}")
        httpd.serve_forever()
