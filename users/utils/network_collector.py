import platform
import subprocess
import json
import shutil

def collect_firewall_info():
    if platform.system() != "Windows":
        return {"error": "Not Windows"}

    try:
        powershell = shutil.which("powershell") or "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe"
        cmd = [
            powershell,
            "-NoProfile",
            "-ExecutionPolicy", "Bypass",
            "-Command",
            "Get-NetFirewallProfile | Select-Object Name,Enabled | ConvertTo-Json"
        ]
        out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, text=True, timeout=6)
        parsed = json.loads(out)
        if isinstance(parsed, dict):
            parsed = [parsed]
        return parsed
    except Exception as e:
        print("❌ Firewall info error:", e)
        return [{"error": str(e)}]
