"""
Suricata Alert Collector Module
================================

This module provides functionality to collect and parse Suricata IDS/IPS alerts
from the EVE JSON log file format.

Suricata generates alerts in a structured JSON format called EVE (Extensible
Value Format). Each line in the EVE log is a complete JSON object containing
event data.

Usage:
    from users.utils.suricata_collector import collect_suricata_alerts
    alerts = collect_suricata_alerts(limit=50)
"""

import json
import os
import logging
from datetime import datetime
from typing import List, Dict, Any

# Logger configuration
logger = logging.getLogger(__name__)

# Default Suricata EVE log path
SURICATA_EVE_LOG = "/var/log/suricata/eve.json"

# Severity mapping
SEVERITY_MAP = {
    "1": "High",
    "2": "Medium",
    "3": "Low",
    "4": "Info",
    1: "High",
    2: "Medium",
    3: "Low",
    4: "Info"
}


def collect_suricata_alerts(log_path: str = SURICATA_EVE_LOG, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Collect Suricata alerts from EVE JSON log file.
    
    Args:
        log_path: Path to Suricata EVE log file (default: /var/log/suricata/eve.json)
        limit: Maximum number of alerts to return (default: 50)
    
    Returns:
        List of parsed alert dictionaries with structured data
    
    Example:
        >>> alerts = collect_suricata_alerts(limit=10)
        >>> for alert in alerts:
        ...     print(f"{alert['timestamp']}: {alert['message']}")
    """
    alerts = []
    
    # Check if log file exists
    if not os.path.exists(log_path):
        logger.warning(f"Suricata EVE log file not found: {log_path}")
        return alerts
    
    try:
        with open(log_path, 'r') as f:
            # Read last 'limit' lines
            lines = f.readlines()
            lines = lines[-limit:] if len(lines) > limit else lines
        
        # Parse each line as JSON
        for line in lines:
            try:
                if line.strip():
                    event = json.loads(line)
                    parsed_alert = parse_suricata_event(event)
                    if parsed_alert:
                        alerts.append(parsed_alert)
            except json.JSONDecodeError as e:
                logger.debug(f"Failed to parse JSON line: {e}")
                continue
        
        logger.info(f"Collected {len(alerts)} Suricata alerts")
        return alerts
    
    except Exception as e:
        logger.error(f"Error reading Suricata EVE log: {e}")
        return alerts


def parse_suricata_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse a single Suricata EVE event into a structured alert dictionary.
    
    Args:
        event: Raw Suricata event dictionary from EVE log
    
    Returns:
        Structured alert dictionary with extracted fields
    
    Example EVE Event Structure:
        {
            "timestamp": "2025-10-18T04:17:03.123456+0000",
            "flow_id": 1234567890,
            "in_iface": "eth0",
            "event_type": "alert",
            "src_ip": "192.168.1.100",
            "src_port": 54321,
            "dest_ip": "8.8.8.8",
            "dest_port": 53,
            "proto": "UDP",
            "alert": {
                "action": "allowed",
                "gid": 1,
                "signature_id": 2210001,
                "rev": 7,
                "signature": "Potential DNS Tunneling Activity",
                "category": "Protocol Command Decode",
                "severity": 2
            }
        }
    """
    try:
        alert_data = {
            "timestamp": event.get("timestamp", ""),
            "event_type": event.get("event_type", "unknown"),
            "flow_id": event.get("flow_id", ""),
            "in_iface": event.get("in_iface", ""),
            "src_ip": event.get("src_ip", ""),
            "src_port": event.get("src_port", ""),
            "dest_ip": event.get("dest_ip", ""),
            "dest_port": event.get("dest_port", ""),
            "proto": event.get("proto", "").upper(),
            "message": "",
            "severity": "Info",
            "signature_id": "",
            "category": "",
            "action": "logged"
        }
        
        # Extract alert-specific information if event_type is 'alert'
        if "alert" in event:
            alert_info = event["alert"]
            alert_data["message"] = alert_info.get("signature", "")
            alert_data["signature_id"] = alert_info.get("signature_id", "")
            alert_data["category"] = alert_info.get("category", "")
            alert_data["action"] = alert_info.get("action", "logged")
            
            # Map severity number to name
            severity_raw = alert_info.get("severity")
            alert_data["severity"] = SEVERITY_MAP.get(severity_raw, "Info")
        
        # Extract HTTP transaction info if present
        if "http" in event:
            http_info = event["http"]
            alert_data["http_method"] = http_info.get("http_method", "")
            alert_data["http_uri"] = http_info.get("uri", "")
            alert_data["http_host"] = http_info.get("hostname", "")
        
        # Extract DNS info if present
        if "dns" in event:
            dns_info = event["dns"]
            alert_data["dns_query"] = dns_info.get("query", "")
            alert_data["dns_type"] = dns_info.get("type", "")
        
        # Extract file info if present
        if "file_info" in event:
            file_info = event["file_info"]
            alert_data["file_name"] = file_info.get("filename", "")
            alert_data["file_size"] = file_info.get("size", "")
        
        return alert_data
    
    except Exception as e:
        logger.debug(f"Error parsing Suricata event: {e}")
        return None


def get_alert_severity_color(severity: str) -> str:
    """
    Get HTML color code for alert severity level.
    
    Args:
        severity: Severity string ('High', 'Medium', 'Low', 'Info')
    
    Returns:
        Hex color code for the severity
    """
    severity_colors = {
        "High": "#dc3545",      # Red
        "Medium": "#ff9800",    # Orange
        "Low": "#17a2b8",       # Blue
        "Info": "#6c757d"       # Gray
    }
    return severity_colors.get(severity, "#6c757d")


def get_alert_count_by_severity(alerts: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Count alerts by severity level.
    
    Args:
        alerts: List of parsed alerts
    
    Returns:
        Dictionary with severity counts
    
    Example:
        >>> alerts = collect_suricata_alerts()
        >>> counts = get_alert_count_by_severity(alerts)
        >>> print(counts)
        {'High': 5, 'Medium': 12, 'Low': 3, 'Info': 1}
    """
    counts = {
        "High": 0,
        "Medium": 0,
        "Low": 0,
        "Info": 0
    }
    
    for alert in alerts:
        severity = alert.get("severity", "Info")
        if severity in counts:
            counts[severity] += 1
    
    return counts


def get_top_ips(alerts: List[Dict[str, Any]], top_n: int = 10) -> Dict[str, int]:
    """
    Get top source IPs generating alerts.
    
    Args:
        alerts: List of parsed alerts
        top_n: Number of top IPs to return
    
    Returns:
        Dictionary of top IPs with their alert counts
    """
    ip_counts = {}
    
    for alert in alerts:
        src_ip = alert.get("src_ip", "unknown")
        if src_ip:
            ip_counts[src_ip] = ip_counts.get(src_ip, 0) + 1
    
    # Sort by count and return top N
    sorted_ips = sorted(ip_counts.items(), key=lambda x: x[1], reverse=True)
    return dict(sorted_ips[:top_n])


def filter_alerts_by_severity(alerts: List[Dict[str, Any]], severity: str) -> List[Dict[str, Any]]:
    """
    Filter alerts by severity level.
    
    Args:
        alerts: List of parsed alerts
        severity: Severity to filter by ('High', 'Medium', 'Low', 'Info')
    
    Returns:
        Filtered list of alerts
    """
    return [alert for alert in alerts if alert.get("severity") == severity]


def filter_alerts_by_ip(alerts: List[Dict[str, Any]], ip_address: str) -> List[Dict[str, Any]]:
    """
    Filter alerts by source IP address.
    
    Args:
        alerts: List of parsed alerts
        ip_address: Source IP to filter by
    
    Returns:
        Filtered list of alerts from specified IP
    """
    return [alert for alert in alerts if alert.get("src_ip") == ip_address]


def export_alerts_to_json(alerts: List[Dict[str, Any]], output_path: str) -> bool:
    """
    Export alerts to JSON file.
    
    Args:
        alerts: List of parsed alerts
        output_path: Path to export file
    
    Returns:
        True if successful, False otherwise
    """
    try:
        with open(output_path, 'w') as f:
            json.dump(alerts, f, indent=2)
        logger.info(f"Exported {len(alerts)} alerts to {output_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to export alerts: {e}")
        return False


def generate_alert_summary(alerts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate a summary report of collected alerts.
    
    Args:
        alerts: List of parsed alerts
    
    Returns:
        Summary dictionary with statistics
    """
    summary = {
        "total_alerts": len(alerts),
        "severity_breakdown": get_alert_count_by_severity(alerts),
        "top_source_ips": get_top_ips(alerts),
        "event_types": {},
        "protocols": {},
        "timestamp_range": {}
    }
    
    # Count by event type
    for alert in alerts:
        event_type = alert.get("event_type", "unknown")
        summary["event_types"][event_type] = summary["event_types"].get(event_type, 0) + 1
    
    # Count by protocol
    for alert in alerts:
        proto = alert.get("proto", "unknown")
        summary["protocols"][proto] = summary["protocols"].get(proto, 0) + 1
    
    # Get time range
    if alerts:
        timestamps = [alert.get("timestamp", "") for alert in alerts if alert.get("timestamp")]
        if timestamps:
            summary["timestamp_range"] = {
                "first": min(timestamps),
                "last": max(timestamps)
            }
    
    return summary


if __name__ == "__main__":
    # Example usage
    print("Suricata Alert Collector")
    print("=" * 50)
    
    # Collect alerts
    alerts = collect_suricata_alerts(limit=20)
    print(f"\nCollected {len(alerts)} alerts")
    
    if alerts:
        # Generate summary
        summary = generate_alert_summary(alerts)
        print("\nAlert Summary:")
        print(f"Total Alerts: {summary['total_alerts']}")
        print(f"Severity Breakdown: {summary['severity_breakdown']}")
        print(f"Top Source IPs: {summary['top_source_ips']}")
        
        # Show first alert details
        print("\nFirst Alert Example:")
        first_alert = alerts[0]
        for key, value in first_alert.items():
            print(f"  {key}: {value}")
