"""
Ultra-simple HTTP server for testing Railway deployment
"""

import http.server
import socketserver
import os
from urllib.parse import urlparse

PORT = int(os.environ.get('PORT', 8000))

class TestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health-simple':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status": "healthy"}')
        elif self.path == '/ping':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status": "pong"}')
        elif self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'<h1>Simple Test Server Running!</h1>')
        else:
            self.send_response(404)
            self.end_headers()

if __name__ == "__main__":
    with socketserver.TCPServer(("", PORT), TestHandler) as httpd:
        print(f"Serving on port {PORT}")
        httpd.serve_forever()