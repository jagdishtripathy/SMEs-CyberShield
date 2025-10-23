import platform
import json
import os
import subprocess
import shutil

def _import_psutil():
    try:
        import psutil
        return psutil
    except Exception:
        return None


def collect_system_snapshot():
    """
    Cross-platform system snapshot collection
    Detects OS and collects appropriate security data
    """
    psutil = _import_psutil()
    
    platform_system = platform.system()  # Windows, Linux, Darwin (macOS)
    
    meta = {
        "platform": platform_system,
        "hostname": platform.node(),
        "arch": platform.machine(),
        "python_version": platform.python_version()
    }

    system = {}
    network = {}

    if psutil:
        system = {
            "cpu": {"cpu_percent": psutil.cpu_percent(interval=1), "cpu_count": psutil.cpu_count()},
            "memory": psutil.virtual_memory()._asdict(),
            "swap": psutil.swap_memory()._asdict(),
            "disks": []
        }
        for p in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(p.mountpoint)._asdict()
            except Exception:
                usage = {"total": None, "used": None, "free": None, "percent": None}
            system["disks"].append({
                "device": p.device,
                "mountpoint": p.mountpoint,
                "fstype": p.fstype,
                "usage": usage
            })

    # Collect OS-specific security data
    snapshot = {"meta": meta, "system": system, "network": network}

    # Windows: Collect Defender and Windows Firewall
    if platform_system == "Windows":
        try:
            from .defender_collector import collect_defender_info
            snapshot["defender"] = collect_defender_info()
        except Exception as e:
            snapshot["defender"] = {"error": f"defender: {e}"}

        try:
            from .network_collector import collect_firewall_info
            snapshot["firewall"] = collect_firewall_info()
        except Exception as e:
            snapshot["firewall"] = {"error": f"firewall: {e}"}

    # Linux: Collect Linux-specific security info
    elif platform_system == "Linux":
        try:
            from .firewall_collector_linux import collect_firewall_info as collect_firewall_linux
            snapshot["firewall"] = collect_firewall_linux()
        except Exception as e:
            snapshot["firewall"] = {"error": f"firewall: {e}"}

        try:
            from .antivirus_collector_linux import collect_antivirus_info
            snapshot["antivirus"] = collect_antivirus_info()
        except Exception as e:
            snapshot["antivirus"] = {"error": f"antivirus: {e}"}

    # macOS: Can be added later
    elif platform_system == "Darwin":
        snapshot["defender"] = {"info": "macOS system detected"}
        snapshot["firewall"] = {"info": "macOS firewall detection not yet implemented"}

    return snapshot
