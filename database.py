"""Database module for FutLive Bot"""
import sqlite3
import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

DB_PATH = os.path.join(os.path.dirname(__file__), 'futlive.db')

class Database:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, team_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(user_id, team_name))''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, match_id TEXT,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS match_views (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, match_id TEXT,
            viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS event_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT, event_type TEXT, message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS stats (key TEXT PRIMARY KEY, value INTEGER DEFAULT 0)''')
        cursor.execute('INSERT OR IGNORE INTO stats (key, value) VALUES (?, ?)', ('total_users', 0))
        cursor.execute('INSERT OR IGNORE INTO stats (key, value) VALUES (?, ?)', ('notifications_sent', 0))
        conn.commit()
        conn.close()

    def register_user(self, user_id: int, username: Optional[str] = None, first_name: Optional[str] = None):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO users (user_id, username, first_name, last_active)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP) ON CONFLICT(user_id) DO UPDATE SET
            username = excluded.username, first_name = excluded.first_name, last_active = CURRENT_TIMESTAMP''', (user_id, username, first_name))
        cursor.execute('UPDATE stats SET value = (SELECT COUNT(*) FROM users) WHERE key = ?', ('total_users',))
        conn.commit()
        conn.close()

    def add_team_subscription(self, user_id: int, team_name: str) -> bool:
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute('INSERT INTO subscriptions (user_id, team_name) VALUES (?, ?)', (user_id, team_name))
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            return False

    def remove_team_subscription(self, user_id: int, team_name: str) -> bool:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM subscriptions WHERE user_id = ? AND team_name = ?', (user_id, team_name))
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return deleted

    def get_user_teams(self, user_id: int) -> List[str]:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT team_name FROM subscriptions WHERE user_id = ?', (user_id,))
        teams = [row[0] for row in cursor.fetchall()]
        conn.close()
        return teams

    def get_teams_count(self, user_id: int) -> int:
        return len(self.get_user_teams(user_id))

    def get_all_subscribers(self) -> Dict[int, List[str]]:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT user_id, team_name FROM subscriptions')
        result: Dict[int, List[str]] = {}
        for row in cursor.fetchall():
            if row[0] not in result:
                result[row[0]] = []
            result[row[0]].append(row[1])
        conn.close()
        return result

    def was_notification_sent(self, user_id: int, match_id: str) -> bool:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT 1 FROM notifications WHERE user_id = ? AND match_id = ?', (user_id, match_id))
        exists = cursor.fetchone() is not None
        conn.close()
        return exists

    def mark_notification_sent(self, user_id: int, match_id: str):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('INSERT OR IGNORE INTO notifications (user_id, match_id) VALUES (?, ?)', (user_id, match_id))
        cursor.execute('UPDATE stats SET value = value + 1 WHERE key = ?', ('notifications_sent',))
        conn.commit()
        conn.close()

    def clear_old_notifications(self, hours: int = 24):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM notifications WHERE sent_at < datetime("now", ?)', (f'-{hours} hours',))
        conn.commit()
        conn.close()

    def log_match_view(self, user_id: int, match_id: str):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO match_views (user_id, match_id) VALUES (?, ?)', (user_id, match_id))
        conn.commit()
        conn.close()

    def log_event(self, event_type: str, message: str):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO event_log (event_type, message) VALUES (?, ?)', (event_type, message))
        conn.commit()
        conn.close()

    def get_full_stats(self) -> Dict[str, Any]:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT key, value FROM stats')
        main_stats = {row[0]: row[1] for row in cursor.fetchall()}
        cursor.execute('SELECT COUNT(DISTINCT user_id) FROM users WHERE last_active > datetime("now", "-7 days")')
        active_week = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM subscriptions')
        total_subscriptions = cursor.fetchone()[0]
        conn.close()
        return {'main': main_stats, 'active_week': active_week, 'total_subscriptions': total_subscriptions}

db = Database()
