import http.server
import socketserver
import os

PORT = int(os.environ.get('PORT', 8080))
socketserver.TCPServer(("", PORT), http.server.SimpleHTTPRequestHandler).serve_forever()
