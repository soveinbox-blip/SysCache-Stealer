# SysCache-Stealer - Advanced Infostealer (PoC)

**Author:** NicoSove  
**Institute:** ITS Angelo Rizzoli  
**Course:** UFS-19 Red Teaming  
**Exam Project:** Proposta 4 (Keylogger) + Advanced Extensions

---

## Legal Disclaimer

> **This project was developed strictly for educational and didactic purposes.**
>
> It was created as part of a cybersecurity exam to demonstrate the mechanics of malware, data collection, and exfiltration in a **controlled laboratory environment**. The author does not condone or support the use of this software for malicious, illegal, or unauthorized purposes. **Do not execute this script on machines you do not own or do not have explicit permission to test.**
>
> **This is a fully simulated school project and must not be used outside of a safe, controlled environment.**

---

## Project Overview

`SysCache-Stealer` is a Proof-of-Concept (PoC) Information Stealer written in Python. While the core exam requirement was a simple keylogger, this tool was extended to simulate a realistic Red Teaming post-exploitation phase.

It combines keystroke logging, clipboard hijacking, system reconnaissance, credential harvesting, and automated data exfiltration to a Command and Control (C2) server.

---

## Repository Structure

```
SysCache-Stealer/
|
+-- README.md
+-- .gitignore
+-- requirements.txt
|
+-- windows_payload/
|   +-- keylogger_vittima.py
|   +-- persistence.py
|
+-- kali_c2_server/
    +-- server.py
```

---

## Features

- **Automated Dependency Installation:** Automatically installs required Python libraries (`pynput`, `mss`, `pyperclip`) upon execution.
- **Keystroke Logging:** Captures all keyboard inputs.
- **Human-Readable Parser:** Reconstructs raw keystrokes into readable sentences, intelligently handling backspaces and spaces.
- **Clipboard Hijacking:** Monitors the clipboard every 3 seconds to capture copied passwords.
- **Browser History Extraction:** Extracts the last 100 visited URLs from Firefox, Google Chrome, and Microsoft Edge.
- **Wi-Fi Credential Harvesting:** Uses Windows native `netsh` utilities to extract saved Wi-Fi SSIDs and plaintext passwords.
- **System Reconnaissance:** Collects OS version, username, hostname, and Public IP.
- **Silent Screenshots:** Takes a screenshot every 60 seconds.
- **Automated Exfiltration:** Every 5 minutes, zips screenshots and sends all logs to the C2 server via HTTP POST.
- **Smart Login Detection (Trigger):** Monitors browser history every 30 seconds. If a new URL matching login patterns (e.g., `login`, `signin`) is detected, it instantly triggers an exfiltration.
- **Persistence (HKCU Run Key):** On first execution, the payload copies itself to `%LOCALAPPDATA%\SysCache\svchost.py` and registers a `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` entry (`SysCacheSvc`) so it relaunches automatically at every user logon — without requiring Administrator privileges.
- **Console-less Relaunch:** Uses `pythonw.exe` when available so the persistent instance runs without a visible console window.
- **Idempotent Install:** Detects an existing Run entry and refreshes the staged copy instead of creating duplicates.
- **Heartbeat Beacon:** Sends a one-time `heartbeat_<HOSTNAME>.txt` to the C2 on each launch, reporting hostname, user, timestamp, and persistence status.
- **Clean Uninstall:** `persistence.uninstall()` removes both the Run key and the staged copy for post-demo cleanup.

---

## Architecture & Data Flow

1. **Reconnaissance:** On startup, gathers System Info, Wi-Fi passwords, and sends them immediately.
2. **Collection:** Background threads monitor keyboard, mouse, clipboard, and browser SQLite databases.
3. **Staging:** Data is stored locally in `%LOCALAPPDATA%\SysCache`. Screenshots are zipped.
4. **Exfiltration:** Data is sent via HTTP POST to the Kali C2 listener on port `4444`.

---

## Prerequisites

| Component | Requirement |
|---|---|
| **Victim Machine** | Windows 10/11 with Python 3.x |
| **Attacker Machine** | Kali Linux |
| **Network** | Both machines on the same local network (NAT Network / Host-Only) |

---

## Usage Instructions

### 1. Start the C2 Server (Kali Linux)

```bash
cd kali_c2_server
python3 server.py
```

### 2. Configure the Payload

Open `windows_payload/keylogger_vittima.py` and modify the configuration:

```python
ATTACKER_IP   = "192.168.160.129"   # <-- Your Kali IP
ATTACKER_PORT = 4444
```

### 3. Execute the Payload (Windows)

```cmd
cd windows_payload
python keylogger_vittima.py
```

---

## Mitigation & Defense

| Defense | Description |
|---|---|
| **Endpoint Detection and Response (EDR)** | Monitor for anomalous Python processes making outbound HTTP connections. |
| **Application Whitelisting** | Prevent unauthorized scripts from executing. |
| **Browser Database Protection** | Restrict access to SQLite history files while the browser is running. |
| **Network Segmentation** | Egress filtering on the firewall to block unauthorized HTTP POST requests. |
| **CLI Logging** | Monitor Windows Event Logs for `netsh wlan show profile key=clear`. |
| **Run Key Monitoring** | Alert on new `HKCU\...\Run` values — a classic user-mode persistence location. Sysmon Event ID 13/14 or EDR autorun telemetry covers this. |
| **%LOCALAPPDATA% Execution** | Flag `pythonw.exe` (or any interpreter) launching scripts from `%LOCALAPPDATA%` — legitimate software rarely stages interpreters there. |
| **Autoruns Auditing** | Periodic auditing via Autoruns or `Get-CimInstance Win32_StartupCommand` catches masqueraded names like `svchost.py`. |

---

*Developed for the ITS Angelo Rizzoli UFS-19 Red Teaming Final Exam.*
