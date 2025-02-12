import http.server
import socketserver
import os

PORT = 8081
host = os.getenv('HOSTNAME', '0.0.0.0')

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b'<html><body><h1>Web Server is running</h1></body></html>')

if __name__ == "__main__":
    with socketserver.TCPServer((host, PORT), Handler) as httpd:
        print(f"Serving on port {PORT}")
        httpd.serve_forever()
