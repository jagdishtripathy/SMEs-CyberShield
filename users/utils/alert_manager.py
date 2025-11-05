# users/utils/alert_manager.py
# SIEM Alert Manager - Stores alerts in database only

import json
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, Tuple, List, Optional

logger = logging.getLogger(__name__)


class AlertManager:
    """
    Real-time alert manager for SIEM.
    Stores alerts in database - accessible via dashboard.
    """

    def __init__(self, db_path: str):
        self.db_path = db_path

    def get_db_connection(self):
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_tables(self) -> bool:
        """Initialize alert tables in database."""
        conn = self.get_db_connection()
        try:
            # Alert Configuration Table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS alert_config (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_name TEXT UNIQUE NOT NULL,
                    enabled BOOLEAN DEFAULT 1,
                    severity_threshold TEXT DEFAULT 'High',
                    cooldown_seconds INTEGER DEFAULT 300,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Alerts History Table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS alerts_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    source_ip TEXT,
                    dest_ip TEXT,
                    message TEXT NOT NULL,
                    event_data TEXT,
                    acknowledged BOOLEAN DEFAULT 0,
                    acknowledged_by TEXT,
                    acknowledged_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            conn.commit()
            logger.info("✅ Alert tables initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Error initializing alert tables: {e}")
            return False
        finally:
            conn.close()

    # =====================
    # ALERT CONFIGURATION
    # =====================

    def create_alert_config(self, alert_name: str, severity: str = 'High',
                          cooldown: int = 300, enabled: bool = True) -> bool:
        """Create new alert configuration (SIEM-only).
        Params:
            alert_name: Unique name for the alert rule/type
            severity: One of ['Critical', 'High', 'Medium', 'Low'] used as threshold
            cooldown: Minimum seconds between consecutive alerts of same type
            enabled: Whether this alert rule is active
        """
        conn = self.get_db_connection()
        try:
            conn.execute('''
                INSERT INTO alert_config 
                (alert_name, severity_threshold, cooldown_seconds, enabled)
                VALUES (?, ?, ?, ?)
            ''', (alert_name, severity, cooldown, 1 if enabled else 0))
            conn.commit()
            logger.info(f"Alert config created: {alert_name}")
            return True
        except Exception as e:
            logger.error(f"Error creating alert config: {e}")
            return False
        finally:
            conn.close()

    def get_all_alert_configs(self) -> List[Dict]:
        """Get all alert configurations."""
        conn = self.get_db_connection()
        try:
            configs = conn.execute('SELECT * FROM alert_config').fetchall()
            return [dict(row) for row in configs]
        finally:
            conn.close()

    def get_alert_config(self, alert_name: str) -> Optional[Dict]:
        """Get specific alert configuration."""
        conn = self.get_db_connection()
        try:
            config = conn.execute(
                'SELECT * FROM alert_config WHERE alert_name = ?',
                (alert_name,)
            ).fetchone()
            return dict(config) if config else None
        finally:
            conn.close()

    def update_alert_config(self, alert_name: str, **kwargs) -> bool:
        """Update alert configuration (SIEM-only)."""
        conn = self.get_db_connection()
        try:
            # Only SIEM-local fields are supported
            allowed_fields = ['enabled', 'severity_threshold', 'cooldown_seconds']

            updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
            updates['updated_at'] = datetime.now().isoformat()

            if not updates:
                return False

            set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
            values = list(updates.values()) + [alert_name]

            conn.execute(f'UPDATE alert_config SET {set_clause} WHERE alert_name = ?', values)
            conn.commit()
            logger.info(f"Alert config updated: {alert_name}")
            return True
        except Exception as e:
            logger.error(f"Error updating alert config: {e}")
            return False
        finally:
            conn.close()

    # =====================
    # ALERT DETECTION
    # =====================

    def should_alert(self, alert_type: str, severity: str) -> Tuple[bool, str]:
        """
        Check if alert should be sent based on configuration and cooldown.
        Returns: (should_send: bool, reason: str)
        """
        conn = self.get_db_connection()
        try:
            config = conn.execute(
                'SELECT * FROM alert_config WHERE alert_name = ?',
                (alert_type,)
            ).fetchone()

            if not config:
                return False, f"No config for {alert_type}"

            if not config['enabled']:
                return False, f"Alert {alert_type} disabled"

            # Check severity threshold
            severity_order = {'Critical': 0, 'High': 1, 'Medium': 2, 'Low': 3}
            threshold = severity_order.get(config['severity_threshold'], 999)
            current = severity_order.get(severity, 999)

            if current > threshold:
                return False, f"Severity {severity} below threshold"

            # Check cooldown
            cooldown = config['cooldown_seconds']
            last_alert = conn.execute('''
                SELECT created_at FROM alerts_history
                WHERE alert_type = ?
                ORDER BY created_at DESC
                LIMIT 1
            ''', (alert_type,)).fetchone()

            if last_alert:
                last_time = datetime.fromisoformat(last_alert['created_at'])
                time_since = (datetime.now() - last_time).total_seconds()
                if time_since < cooldown:
                    return False, f"In cooldown ({int(cooldown - time_since)}s remaining)"
            return True, "OK"
        finally:
            conn.close()

    # =====================
    # ALERT STORAGE
    # =====================

    def store_alert(self, alert_type: str, severity: str, source_ip: str,
                   dest_ip: str, message: str, event_data: str = None) -> int:
        """Store alert in database. Returns alert ID."""
        conn = self.get_db_connection()
        try:
            cursor = conn.execute('''
                INSERT INTO alerts_history 
                (alert_type, severity, source_ip, dest_ip, message, event_data)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (alert_type, severity, source_ip, dest_ip, message, event_data or ''))
            conn.commit()
            alert_id = cursor.lastrowid
            logger.info(f"Alert stored with ID: {alert_id}")
            # Fire-and-forget notification to external channels (Discord, etc.)
            try:
                # Local import to avoid import cycles and make the notifier optional
                from utils.alert_notifier import notify
                from threading import Thread

                alert_obj = {
                    "id": alert_id,
                    "title": alert_type,
                    "message": message,
                    "severity": severity,
                    "source_ip": source_ip,
                    "dest_ip": dest_ip,
                    "event_data": event_data,
                    "timestamp": datetime.now().isoformat()
                }

                Thread(target=notify, args=(alert_obj,), daemon=True).start()
            except Exception as e:
                logger.warning(f"Alert notification failed to start: {e}")

            return alert_id
        except Exception as e:
            logger.error(f"Error storing alert: {e}")
            return -1
        finally:
            conn.close()

    def acknowledge_alert(self, alert_id: int, admin_id: int) -> bool:
        """Mark alert as acknowledged."""
        conn = self.get_db_connection()
        try:
            conn.execute('''
                UPDATE alerts_history
                SET acknowledged = 1, acknowledged_by = ?, acknowledged_at = ?
                WHERE id = ?
            ''', (admin_id, datetime.now().isoformat(), alert_id))
            conn.commit()
            logger.info(f"Alert {alert_id} acknowledged by admin {admin_id}")
            return True
        except Exception as e:
            logger.error(f"Error acknowledging alert: {e}")
            return False
        finally:
            conn.close()

    # =====================
    # ALERT RETRIEVAL
    # =====================

    def get_recent_alerts(self, limit: int = 50) -> List[Dict]:
        """Get recent alerts."""
        conn = self.get_db_connection()
        try:
            alerts = conn.execute('''
                SELECT * FROM alerts_history
                ORDER BY created_at DESC
                LIMIT ?
            ''', (limit,)).fetchall()
            return [dict(row) for row in alerts]
        finally:
            conn.close()

    def get_unacknowledged_alerts(self) -> List[Dict]:
        """Get unacknowledged alerts."""
        conn = self.get_db_connection()
        try:
            alerts = conn.execute('''
                SELECT * FROM alerts_history
                WHERE acknowledged = 0
                ORDER BY created_at DESC
            ''').fetchall()
            return [dict(row) for row in alerts]
        finally:
            conn.close()

    def get_alerts_by_severity(self, severity: str, limit: int = 50) -> List[Dict]:
        """Get alerts by severity level."""
        conn = self.get_db_connection()
        try:
            alerts = conn.execute('''
                SELECT * FROM alerts_history
                WHERE severity = ?
                ORDER BY created_at DESC
                LIMIT ?
            ''', (severity, limit)).fetchall()
            return [dict(row) for row in alerts]
        finally:
            conn.close()

    def get_alert_statistics(self) -> Dict:
        """Get alert statistics."""
        conn = self.get_db_connection()
        try:
            stats = {
                'total_alerts': conn.execute('SELECT COUNT(*) as count FROM alerts_history').fetchone()['count'],
                'unacknowledged': conn.execute('SELECT COUNT(*) as count FROM alerts_history WHERE acknowledged = 0').fetchone()['count'],
                'critical': conn.execute('SELECT COUNT(*) as count FROM alerts_history WHERE severity = "Critical"').fetchone()['count'],
                'high': conn.execute('SELECT COUNT(*) as count FROM alerts_history WHERE severity = "High"').fetchone()['count'],
                'medium': conn.execute('SELECT COUNT(*) as count FROM alerts_history WHERE severity = "Medium"').fetchone()['count'],
                'low': conn.execute('SELECT COUNT(*) as count FROM alerts_history WHERE severity = "Low"').fetchone()['count'],
            }
            return stats
        finally:
            conn.close()

    # =====================
    # UTILITY METHODS
    # =====================

    def delete_old_alerts(self, days: int = 30) -> int:
        """Delete alerts older than specified days."""
        conn = self.get_db_connection()
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            cursor = conn.execute('''
                DELETE FROM alerts_history
                WHERE created_at < ?
            ''', (cutoff_date,))
            conn.commit()
            deleted = cursor.rowcount
            logger.info(f"✅ Deleted {deleted} alerts older than {days} days")
            return deleted
        except Exception as e:
            logger.error(f"Error deleting old alerts: {e}")
            return 0
        finally:
            conn.close()
