import platform
import subprocess
import json
import shutil

def collect_defender_info():
    if platform.system() != "Windows":
        return {"info": "Not Windows"}

    try:
        powershell = shutil.which("powershell") or "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe"
        cmd = [
            powershell,
            "-NoProfile",
            "-ExecutionPolicy", "Bypass",
            "-Command",
            "Get-MpComputerStatus | ConvertTo-Json -Depth 3"
        ]
        out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, text=True, timeout=6)
        data = json.loads(out)
        return {
            "AntivirusEnabled": bool(data.get("AntivirusEnabled")),
            "RealTimeProtectionEnabled": bool(data.get("RealTimeProtectionEnabled")),
            "AntivirusSignatureAge": data.get("AntivirusSignatureAge", 0)
        }
    except Exception as e:
        print("❌ Defender info error:", e)
        return {"error": str(e)}
