import platform
import subprocess
import json

def collect_firewall_info():
    """
    Collect firewall information on Linux systems
    Supports: iptables, ufw, firewalld
    """
    if platform.system() != "Linux":
        return {"error": "Not Linux"}

    firewall_info = {}

    # Check for UFW (Uncomplicated Firewall)
    try:
        result = subprocess.run(['sudo', 'ufw', 'status'], 
                              capture_output=True, 
                              text=True, 
                              timeout=5)
        if result.returncode == 0:
            firewall_info['ufw'] = {
                'enabled': 'active' in result.stdout.lower() or 'enabled' in result.stdout.lower(),
                'status': result.stdout.strip().split('\n')[0]  # First line shows status
            }
    except Exception as e:
        firewall_info['ufw'] = {'error': str(e)}

    # Check for firewalld
    try:
        result = subprocess.run(['sudo', 'systemctl', 'is-active', 'firewalld'],
                              capture_output=True,
                              text=True,
                              timeout=5)
        firewall_info['firewalld'] = {
            'enabled': result.returncode == 0,
            'status': result.stdout.strip()
        }
    except Exception as e:
        firewall_info['firewalld'] = {'error': str(e)}

    # Check iptables rules count
    try:
        result = subprocess.run(['sudo', 'iptables', '-L', '-n'],
                              capture_output=True,
                              text=True,
                              timeout=5)
        rules_count = result.stdout.count('target')  # Rough count
        firewall_info['iptables'] = {
            'installed': result.returncode == 0,
            'rules_count': rules_count
        }
    except Exception as e:
        firewall_info['iptables'] = {'error': str(e)}

    return firewall_info if firewall_info else {"info": "Firewall data collected", "platform": "Linux"}
