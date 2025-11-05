import os
import json
import logging
import time
from typing import Dict

import requests

logger = logging.getLogger(__name__)

DISCORD_WEBHOOK = os.getenv('DISCORD_WEBHOOK_URL')
NOTIFIER_RETRIES = int(os.getenv('NOTIFIER_RETRIES', '3'))
NOTIFIER_TIMEOUT = int(os.getenv('NOTIFIER_TIMEOUT', '10'))


def send_discord_alert(alert: Dict) -> bool:
    """Send an alert to Discord via incoming webhook.

    alert: dict with keys like 'id','title','message','severity','timestamp','source_ip','dest_ip'
    Returns True on success, False otherwise.
    """
    if not DISCORD_WEBHOOK:
        logger.debug("Discord webhook not configured; skipping Discord notification.")
        return False

    embed = {
        "title": alert.get("title", "SIEM Alert"),
        "description": alert.get("message", ""),
        "color": 15158332 if str(alert.get("severity", "")).lower() in ("critical", "high") else 16776960,
        "fields": []
    }

    # Add helpful fields
    if alert.get("severity"):
        embed["fields"].append({"name": "Severity", "value": str(alert.get("severity")), "inline": True})
    if alert.get("source_ip"):
        embed["fields"].append({"name": "Source", "value": str(alert.get("source_ip")), "inline": True})
    if alert.get("dest_ip"):
        embed["fields"].append({"name": "Destination", "value": str(alert.get("dest_ip")), "inline": True})
    if alert.get("timestamp"):
        embed["timestamp"] = alert.get("timestamp")

    payload = {
        "embeds": [embed],
        "content": f"**{embed['title']}**"
    }

    # Try with retries and backoff
    backoff = 1
    for attempt in range(1, NOTIFIER_RETRIES + 1):
        try:
            resp = requests.post(DISCORD_WEBHOOK, json=payload, timeout=NOTIFIER_TIMEOUT)
            if resp.status_code in (200, 204):
                logger.info("Discord notification sent")
                return True
            elif resp.status_code == 429:
                # Rate limited - respect Retry-After header if present
                retry_after = int(resp.headers.get("Retry-After", backoff))
                logger.warning(f"Discord rate limited: retrying after {retry_after}s")
                time.sleep(retry_after)
            else:
                logger.warning(f"Discord webhook failed: {resp.status_code} {resp.text}")
                # Retry with backoff
                time.sleep(backoff)
                backoff *= 2
        except Exception as e:
            logger.error(f"Error sending Discord notification: {e}")
            time.sleep(backoff)
            backoff *= 2

    logger.error("Discord notification failed after retries")
    return False


def notify(alert: Dict) -> None:
    """Generic notify function - currently calls Discord if configured.
    This function intentionally swallows exceptions so callers can fire-and-forget.
    """
    try:
        send_discord_alert(alert)
    except Exception as e:
        logger.error(f"Notifier encountered an error: {e}")
