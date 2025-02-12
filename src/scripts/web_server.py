import http.server
import socketserver
import os
import requests
import sys

PORT = 8081
host = os.getenv('HOSTNAME', '0.0.0.0')

if len(sys.argv) < 2:
    print("Usage: python3 web_server.py <database_host>")
    sys.exit(1)

database_host = sys.argv[1]
database_port = 8082

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # Query the fake database service
        item_id = self.path.strip("/")
        url = f"http://{database_host}:{database_port}/{item_id}"
        try:
            response = requests.get(url, timeout=10)  # Increase the request timeout
            item = response.text if response.status_code == 200 else "Item not found"
        except requests.ConnectionError:
            item = "Database service not available"
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(f"<html><body><h1>{item}</h1></body></html>".encode())

if __name__ == "__main__":
    with socketserver.TCPServer((host, PORT), Handler) as httpd:
        print(f"Serving on port {PORT}")
        httpd.serve_forever()