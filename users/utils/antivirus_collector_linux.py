import platform
import subprocess
import json

def collect_antivirus_info():
    """
    Collect antivirus/security software information on Linux systems
    Supports: ClamAV, Sophos, AIDE, Lynis
    """
    if platform.system() != "Linux":
        return {"error": "Not Linux"}

    antivirus_info = {}

    # Check for ClamAV
    try:
        result = subprocess.run(['clamdtop', '-h'],
                              capture_output=True,
                              text=True,
                              timeout=5)
        clamav_status = subprocess.run(['systemctl', 'is-active', 'clamav-daemon'],
                                     capture_output=True,
                                     text=True,
                                     timeout=5)
        antivirus_info['clamav'] = {
            'installed': result.returncode == 0,
            'enabled': clamav_status.returncode == 0,
            'status': clamav_status.stdout.strip()
        }
    except Exception as e:
        antivirus_info['clamav'] = {'error': str(e)}

    # Check for Sophos
    try:
        result = subprocess.run(['sophos-spl', 'status'],
                              capture_output=True,
                              text=True,
                              timeout=5)
        antivirus_info['sophos'] = {
            'installed': result.returncode == 0,
            'status': result.stdout.strip()
        }
    except Exception as e:
        antivirus_info['sophos'] = {'error': str(e)}

    # Check for AIDE (File Integrity Monitor)
    try:
        result = subprocess.run(['which', 'aide'],
                              capture_output=True,
                              text=True,
                              timeout=5)
        aide_status = subprocess.run(['systemctl', 'is-active', 'aide'],
                                   capture_output=True,
                                   text=True,
                                   timeout=5)
        antivirus_info['aide'] = {
            'installed': result.returncode == 0,
            'enabled': aide_status.returncode == 0,
            'type': 'File Integrity Monitor'
        }
    except Exception as e:
        antivirus_info['aide'] = {'error': str(e)}

    # Check for fail2ban
    try:
        fail2ban_status = subprocess.run(['systemctl', 'is-active', 'fail2ban'],
                                       capture_output=True,
                                       text=True,
                                       timeout=5)
        antivirus_info['fail2ban'] = {
            'installed': fail2ban_status.returncode == 0,
            'enabled': fail2ban_status.returncode == 0,
            'type': 'Intrusion Prevention'
        }
    except Exception as e:
        antivirus_info['fail2ban'] = {'error': str(e)}

    return antivirus_info if antivirus_info else {"info": "Security info collected", "platform": "Linux"}
