"""
Data Manager - Handles all data storage and retrieval using SQLite
"""
import sqlite3
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
from contextlib import contextmanager

class DataManager:
    def __init__(self, db_file: str = 'data/bot_data.db'):
        self.db_file = db_file
        self._init_database()
    
    @contextmanager
    def _get_connection(self):
        """Context manager for database connections"""
        os.makedirs(os.path.dirname(self.db_file), exist_ok=True)
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def _init_database(self):
        """Initialize database tables"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # EClasses table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS eclasses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    eclass_id TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    datetime TEXT NOT NULL,
                    end_datetime TEXT,
                    duration INTEGER,
                    year TEXT,
                    subject TEXT,
                    category TEXT,
                    channel_id INTEGER NOT NULL,
                    teacher_id INTEGER NOT NULL,
                    message_id INTEGER NOT NULL,
                    guild_id INTEGER NOT NULL,
                    channel_message_id INTEGER NOT NULL,
                    status TEXT DEFAULT 'scheduled',
                    started_at TEXT,
                    ended_at TEXT,
                    min_participants INTEGER DEFAULT 0,
                    max_participants INTEGER DEFAULT 0,
                    current_participants INTEGER DEFAULT 0,
                    notified INTEGER DEFAULT 0
                )
            ''')
            
            # Subscriptions table (many-to-many relationship)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS eclass_subscriptions (
                    eclass_id TEXT NOT NULL,
                    user_id INTEGER NOT NULL,
                    subscribed_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (eclass_id, user_id),
                    FOREIGN KEY (eclass_id) REFERENCES eclasses(eclass_id) ON DELETE CASCADE
                )
            ''')
            
            # Statistics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS statistics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT UNIQUE NOT NULL,
                    value INTEGER DEFAULT 0
                )
            ''')
            
            # Initialize statistics if not exist
            cursor.execute('''
                INSERT OR IGNORE INTO statistics (key, value) VALUES 
                ('message_count', 0),
                ('messages_since_sept', 0)
            ''')
            
            conn.commit()
    
    def get_eclasses(self) -> Dict[str, Any]:
        """Get all eclasses"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM eclasses')
            rows = cursor.fetchall()
            
            eclasses = {}
            for row in rows:
                eclass_id = row['eclass_id']
                eclass_data = dict(row)
                
                # Convert notified back to boolean
                eclass_data['notified'] = bool(eclass_data['notified'])
                
                # Get subscribed users
                cursor.execute(
                    'SELECT user_id FROM eclass_subscriptions WHERE eclass_id = ?',
                    (eclass_id,)
                )
                eclass_data['subscribed_users'] = [r['user_id'] for r in cursor.fetchall()]
                
                eclasses[eclass_id] = eclass_data
            
            return eclasses
    
    def get_eclass(self, eclass_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific eclass"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM eclasses WHERE eclass_id = ?', (eclass_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            eclass_data = dict(row)
            eclass_data['notified'] = bool(eclass_data['notified'])
            
            # Get subscribed users
            cursor.execute(
                'SELECT user_id FROM eclass_subscriptions WHERE eclass_id = ?',
                (eclass_id,)
            )
            eclass_data['subscribed_users'] = [r['user_id'] for r in cursor.fetchall()]
            
            return eclass_data
    
    def get_eclass_by_message_id(self, message_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific eclass by message ID"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM eclasses WHERE message_id = ?', (message_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            eclass_data = dict(row)
            eclass_data['notified'] = bool(eclass_data['notified'])
            
            # Get subscribed users
            cursor.execute(
                'SELECT user_id FROM eclass_subscriptions WHERE eclass_id = ?',
                (row['eclass_id'],)
            )
            eclass_data['subscribed_users'] = [r['user_id'] for r in cursor.fetchall()]
            
            return eclass_data
    
    def add_eclass(self, eclass_data: Dict[str, Any]) -> str:
        """Add a new eclass and return its incremental ID"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Extract subscribed users before inserting
            subscribed_users = eclass_data.pop('subscribed_users', [])
            
            # Convert notified to integer
            notified = 1 if eclass_data.get('notified', False) else 0
            
            # Get the next ID
            cursor.execute('SELECT COALESCE(MAX(id), 0) + 1 as next_id FROM eclasses')
            next_id = cursor.fetchone()['next_id']
            eclass_id = f"EC{next_id:04d}"  # Format: EC0001, EC0002, etc.
            
            cursor.execute('''
                INSERT INTO eclasses (
                    eclass_id, title, description, datetime, end_datetime, duration, year,
                    subject, category, channel_id, teacher_id, message_id, guild_id, channel_message_id,
                    status, started_at, ended_at, min_participants,
                    max_participants, current_participants, notified
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                eclass_id,
                eclass_data['title'],
                eclass_data['description'],
                eclass_data['datetime'],
                eclass_data.get('end_datetime'),
                eclass_data.get('duration'),
                eclass_data.get('year'),
                eclass_data.get('subject'),
                eclass_data.get('category'),
                eclass_data['channel_id'],
                eclass_data['teacher_id'],
                eclass_data['message_id'],
                eclass_data['guild_id'],
                eclass_data['channel_message_id'],
                eclass_data.get('status', 'scheduled'),
                eclass_data.get('started_at'),
                eclass_data.get('ended_at'),
                eclass_data.get('min_participants', 0),
                eclass_data.get('max_participants', 0),
                eclass_data.get('current_participants', 0),
                notified
            ))
            
            # Add subscriptions
            for user_id in subscribed_users:
                cursor.execute(
                    'INSERT OR IGNORE INTO eclass_subscriptions (eclass_id, user_id) VALUES (?, ?)',
                    (eclass_id, user_id)
                )
            
            conn.commit()
            return eclass_id
    
    def update_eclass(self, eclass_id: str, updates: Dict[str, Any]):
        """Update an existing eclass"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Handle subscribed_users separately
            if 'subscribed_users' in updates:
                subscribed_users = updates.pop('subscribed_users')
                
                # Clear existing subscriptions
                cursor.execute(
                    'DELETE FROM eclass_subscriptions WHERE eclass_id = ?',
                    (eclass_id,)
                )
                
                # Add new subscriptions
                for user_id in subscribed_users:
                    cursor.execute(
                        'INSERT OR IGNORE INTO eclass_subscriptions (eclass_id, user_id) VALUES (?, ?)',
                        (eclass_id, user_id)
                    )
            
            # Handle notified boolean to integer conversion
            if 'notified' in updates:
                updates['notified'] = 1 if updates['notified'] else 0
            
            # Build UPDATE query dynamically
            if updates:
                set_clause = ', '.join([f'{key} = ?' for key in updates.keys()])
                values = list(updates.values()) + [eclass_id]
                
                cursor.execute(
                    f'UPDATE eclasses SET {set_clause} WHERE eclass_id = ?',
                    values
                )
            
            conn.commit()
    
    def delete_eclass(self, eclass_id: str):
        """Delete an eclass"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM eclass_subscriptions WHERE eclass_id = ?', (eclass_id,))
            cursor.execute('DELETE FROM eclasses WHERE eclass_id = ?', (eclass_id,))
            conn.commit()
    
    def increment_message_count(self, message_date: datetime):
        """Increment message counters"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Increment total message count
            cursor.execute(
                'UPDATE statistics SET value = value + 1 WHERE key = ?',
                ('message_count',)
            )
            
            # Check if message is after September 1st
            sept_1st = datetime(datetime.now().year, 9, 1)
            if message_date.replace(tzinfo=None) >= sept_1st:
                cursor.execute(
                    'UPDATE statistics SET value = value + 1 WHERE key = ?',
                    ('messages_since_sept',)
                )
            
            conn.commit()
    
    def get_message_stats(self) -> Dict[str, int]:
        """Get message statistics"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT key, value FROM statistics WHERE key IN (?, ?)',
                         ('message_count', 'messages_since_sept'))
            
            stats = {'total': 0, 'since_sept': 0}
            for row in cursor.fetchall():
                if row['key'] == 'message_count':
                    stats['total'] = row['value']
                elif row['key'] == 'messages_since_sept':
                    stats['since_sept'] = row['value']
            
            return stats
    
    def count_eclasses_since_sept(self) -> int:
        """Count eclasses created since September 1st"""
        sept_1st = datetime(datetime.now().year, 9, 1).isoformat()
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT COUNT(*) as count FROM eclasses WHERE datetime >= ?',
                (sept_1st,)
            )
            result = cursor.fetchone()
            return result['count'] if result else 0
    
    def get_total_eclass_hours_since_sept(self) -> Dict[str, int]:
        """Get total hours of completed eclasses since September 1st"""
        sept_1st = datetime(datetime.now().year, 9, 1).isoformat()
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT started_at, ended_at 
                FROM eclasses 
                WHERE datetime >= ? AND status = 'completed' 
                AND started_at IS NOT NULL AND ended_at IS NOT NULL
            ''', (sept_1st,))
            
            rows = cursor.fetchall()
            total_minutes = 0
            
            for row in rows:
                try:
                    start = datetime.fromisoformat(row['started_at'])
                    end = datetime.fromisoformat(row['ended_at'])
                    duration = (end - start).total_seconds() / 60  # Convert to minutes
                    total_minutes += duration
                except (ValueError, TypeError):
                    continue
            
            # Convert to hours and minutes
            hours = int(total_minutes // 60)
            minutes = int(total_minutes % 60)
            return {'hours': hours, 'minutes': minutes}
    
    def get_teacher_statistics(self) -> List[Dict[str, Any]]:
        """Get statistics for each teacher who has given at least one completed class"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    teacher_id,
                    COUNT(*) as total_classes,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_classes,
                    MAX(max_participants) as max_participants
                FROM eclasses
                GROUP BY teacher_id
                HAVING completed_classes > 0
                ORDER BY completed_classes DESC, total_classes DESC
            ''')
            
            teachers = []
            for row in cursor.fetchall():
                teacher_id = row['teacher_id']
                
                # Calculate total hours for this teacher
                cursor.execute('''
                    SELECT started_at, ended_at
                    FROM eclasses
                    WHERE teacher_id = ? AND status = 'completed'
                    AND started_at IS NOT NULL AND ended_at IS NOT NULL
                ''', (teacher_id,))
                
                total_minutes = 0
                for class_row in cursor.fetchall():
                    try:
                        start = datetime.fromisoformat(class_row['started_at'])
                        end = datetime.fromisoformat(class_row['ended_at'])
                        duration = (end - start).total_seconds() / 60
                        total_minutes += duration
                    except (ValueError, TypeError):
                        continue
                
                # Convert to hours and minutes
                hours = int(total_minutes // 60)
                minutes = int(total_minutes % 60)
                
                teachers.append({
                    'teacher_id': teacher_id,
                    'total_classes': row['total_classes'],
                    'completed_classes': row['completed_classes'],
                    'total_hours': hours,
                    'total_minutes': minutes,
                    'max_participants': row['max_participants'] or 0
                })
            
            return teachers

