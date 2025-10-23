# app/utils/scoring.py
"""
Simple, explainable scoring engine.
We compute subscores and weight them:
- Defender/AV: 35%
- Firewall: 25%
- System health (CPU/memory/disk): 20%
- Updates & other (placeholder): 20%
"""
def _score_defender(defender):
    if not defender or "error" in defender:
        return 0
    # defender is expected to include booleans like RealTimeProtectionEnabled
    try:
        base = 50
        if defender.get("RealTimeProtectionEnabled"):
            base += 30
        if defender.get("AntivirusEnabled"):
            base += 20
        # reduce if signatures are old
        sig_age = defender.get("AntivirusSignatureAge")
        if sig_age is not None:
            if sig_age > 30:
                base -= 20
            elif sig_age > 7:
                base -= 5
        return max(0, min(100, base))
    except Exception:
        return 30

def _score_firewall(firewall):
    # firewall can be list of profiles on Windows with Enabled=1|0 or dict for other OS.
    try:
        if not firewall:
            return 0
        if isinstance(firewall, list):
            enabled = sum(1 for p in firewall if int(p.get("Enabled", 0)) in (1, True))
            score = int((enabled / max(1, len(firewall))) * 100)
            return score
        elif isinstance(firewall, dict):
            if firewall.get("error"):
                return 20
            return 70
    except Exception:
        return 30

def _score_system(system):
    # reward healthy resource usage and disk space
    try:
        cpu_percent = system.get("cpu", {}).get("cpu_percent", 0)
        mem_percent = system.get("memory", {}).get("percent", 0)
        disk_usages = system.get("disks", [])
        # if any disk percent > 90 -> penalty
        disk_penalty = 0
        for d in disk_usages:
            try:
                p = d.get("usage", {}).get("percent", 0)
                if p and p > 90:
                    disk_penalty += 30
                elif p and p > 75:
                    disk_penalty += 10
            except Exception:
                continue
        score = 100 - int(max(cpu_percent * 0.6, mem_percent * 0.6)) - int(disk_penalty * 0.5)

        return max(0, min(100, score))
    except Exception:
        return 50

def compute_score(snapshot):
    # snapshot is expected like your data.txt structure
    defender = snapshot.get("defender", {})
    firewall = snapshot.get("firewall", [])
    system = snapshot.get("system", {})

    d_score = _score_defender(defender)
    f_score = _score_firewall(firewall)
    s_score = _score_system(system)
    # placeholder for updates/patches etc
    u_score = 80 if snapshot.get("meta") else 50

    # weights
    final = int((d_score * 0.35) + (f_score * 0.25) + (s_score * 0.20) + (u_score * 0.20))
    # clamp
    final = max(0, min(100, final))
    return final
