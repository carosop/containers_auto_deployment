import http.server
import socketserver
import os
import sys

# Define the port for the HTTP server
PORT = 81
# Bind to 0.0.0.0 to be accessible from any IP address on the host
HOST = "0.0.0.0"

# Fake database content
fake_database = {
    "1": "Welcome to C & P world",
    "2": "Well, now you know what Narnia is",
    "3": "Welcome to Dante, Divina Commedia, your status is still not calculated. Wait in Pulgatorio please!!",
    "4": "The quick brown fox jumps over the lazy dog."
}

class Handler(http.server.SimpleHTTPRequestHandler):
    """
    Custom HTTP request handler to serve data from the fake_database.
    """
    def do_GET(self):
        # Extract the item ID from the request path (e.g., /1, /2)
        item_id = self.path.strip("/")
        # Retrieve the item from the database, or return "Item not found"
        item = fake_database.get(item_id, "Item not found")
        
        # Send HTTP 200 OK response
        self.send_response(200)
        # Set Content-type header
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        # Write the response body (encoded to bytes)
        self.wfile.write(item.encode())

if __name__ == "__main__":
    # Ensure standard output is flushed immediately for better logging in Mininet
    sys.stdout.flush() 
    # Create a TCP server that listens on the specified host and port
    with socketserver.TCPServer((HOST, PORT), Handler) as httpd:
        print(f"Database server is running and listening on {HOST}:{PORT}")
        # Serve requests indefinitely
        httpd.serve_forever()
