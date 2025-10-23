# models.py
from datetime import datetime
import json

class User:
    def __init__(self, id, username, email, score=0, badges=None, created_at=None):
        self.id = id
        self.username = username
        self.email = email
        self.score = score
        self.badges = json.loads(badges) if isinstance(badges, str) else badges or []
        self.created_at = created_at or datetime.utcnow()

class Quiz:
    def __init__(self, id, title, questions, category):
        self.id = id
        self.title = title
        self.questions = json.loads(questions) if isinstance(questions, str) else questions
        self.category = category

class URLCheck:
    def __init__(self, id, user_id, url, virustotal_result, gemini_analysis, checked_at):
        self.id = id
        self.user_id = user_id
        self.url = url
        self.virustotal_result = virustotal_result
        self.gemini_analysis = gemini_analysis
        self.checked_at = checked_at

class Snapshot:
    """Simplified Snapshot model without SQLAlchemy."""
    def __init__(self, hostname, platform, created_at=None, raw=None, score=None):
        self.hostname = hostname
        self.platform = platform
        self.created_at = created_at or datetime.utcnow()
        self.raw = json.dumps(raw) if raw else '{}'
        self.score = score or 0

    def set_raw(self, obj):
        self.raw = json.dumps(obj)

    def get_raw(self):
        try:
            return json.loads(self.raw)
        except Exception:
            return {}
