import http.server
import socketserver
import os

PORT = 8082
host = os.getenv('HOSTNAME', '0.0.0.0')

# Fake database
fake_database = {
    "1": "Item 1",
    "2": "Item 2",
    "3": "Item 3"
}

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # Simulate a database query
        item_id = self.path.strip("/")
        item = fake_database.get(item_id, "Item not found")
        
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(item.encode())

if __name__ == "__main__":
    with socketserver.TCPServer((host, PORT), Handler) as httpd:
        print(f"Serving on port {PORT}")
        httpd.serve_forever()