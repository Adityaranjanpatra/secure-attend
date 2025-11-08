"""
Database Management Module
SQLite database for attendance records and user management
Enhanced with Registration Number support
"""

import sqlite3
import datetime
import hashlib
from pathlib import Path
from typing import List, Tuple, Optional, Dict
import numpy as np


class DatabaseManager:
    """SQLite database manager for attendance system"""

    def __init__(self, db_file: str = "attendance.db"):
        self.db_file = Path(db_file)
        self.init_database()
        print(f"✓ Database initialized: {db_file}")

    def init_database(self):
        """Initialize all database tables"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        # Enhanced Users table with registration number
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                registration_number TEXT UNIQUE,
                email TEXT,
                department TEXT,
                phone TEXT,
                registration_date TEXT NOT NULL,
                face_encoding_hash TEXT,
                total_attendance INTEGER DEFAULT 0,
                last_attendance TEXT,
                is_active INTEGER DEFAULT 1,
                is_admin INTEGER DEFAULT 0,
                created_by TEXT,
                notes TEXT
            )
        ''')

        # Enhanced Attendance table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL,
                registration_number TEXT,
                timestamp TEXT NOT NULL,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                liveness_score REAL,
                emotion TEXT,
                engagement_score REAL,
                confidence REAL,
                blockchain_hash TEXT,
                face_encoding_hash TEXT,
                location TEXT,
                device_info TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        ''')

        # Session analytics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS session_analytics (
                session_id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                start_time TEXT,
                end_time TEXT,
                total_attendees INTEGER,
                avg_engagement REAL,
                avg_liveness REAL,
                avg_confidence REAL,
                dominant_emotion TEXT,
                session_type TEXT
            )
        ''')

        # System logs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_logs (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                log_level TEXT,
                module TEXT,
                message TEXT,
                details TEXT
            )
        ''')

        # Create indices for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_attendance_date ON attendance(date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_attendance_user ON attendance(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_regno ON users(registration_number)')

        conn.commit()
        conn.close()

        print("✓ Enhanced database tables created")

    def add_user(self, user_id: str, name: str, face_encoding: np.ndarray,
                 registration_number: str = None, email: str = None,
                 department: str = None, phone: str = None,
                 created_by: str = None) -> bool:
        """Register new user with enhanced fields"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()

            # Check if registration number already exists
            if registration_number:
                cursor.execute('SELECT user_id FROM users WHERE registration_number = ?',
                              (registration_number,))
                if cursor.fetchone():
                    print(f"✗ Registration number {registration_number} already exists")
                    conn.close()
                    return False

            encoding_hash = hashlib.sha256(face_encoding.tobytes()).hexdigest()[:16]
            registration_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            cursor.execute('''
                INSERT OR REPLACE INTO users 
                (user_id, name, registration_number, email, department, phone,
                 registration_date, face_encoding_hash, total_attendance, 
                 is_active, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 1, ?)
            ''', (user_id, name, registration_number, email, department, phone,
                  registration_date, encoding_hash, created_by))

            conn.commit()
            conn.close()

            print(f"✓ User registered: {name} (Reg: {registration_number})")
            return True

        except Exception as e:
            print(f"✗ User registration error: {e}")
            return False

    def mark_attendance(self, user_id: str, name: str, registration_number: str,
                       liveness_score: float, emotion: str, engagement_score: float,
                       blockchain_hash: str, face_encoding: np.ndarray,
                       confidence: float, location: str = "Default") -> Tuple[bool, str]:
        """Mark attendance with registration number"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()

            now = datetime.datetime.now()
            timestamp = now.strftime('%Y-%m-%d %H:%M:%S')
            date = now.strftime('%Y-%m-%d')
            time_str = now.strftime('%H:%M:%S')

            encoding_hash = hashlib.sha256(face_encoding.tobytes()).hexdigest()[:16]

            # Check if already marked today
            cursor.execute('''
                SELECT id FROM attendance 
                WHERE user_id = ? AND date = ?
            ''', (user_id, date))

            if cursor.fetchone():
                conn.close()
                return False, "Already marked today"

            # Insert attendance record
            cursor.execute('''
                INSERT INTO attendance 
                (user_id, name, registration_number, timestamp, date, time, 
                 liveness_score, emotion, engagement_score, confidence, 
                 blockchain_hash, face_encoding_hash, location)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, name, registration_number, timestamp, date, time_str,
                  liveness_score, emotion, engagement_score, confidence,
                  blockchain_hash, encoding_hash, location))

            # Update user statistics
            cursor.execute('''
                UPDATE users 
                SET total_attendance = total_attendance + 1,
                    last_attendance = ?
                WHERE user_id = ?
            ''', (timestamp, user_id))

            conn.commit()
            conn.close()

            print(f"✓ Attendance marked: {name} ({registration_number})")
            return True, "Success"

        except Exception as e:
            print(f"✗ Attendance marking error: {e}")
            return False, str(e)

    def get_attendance_records(self, date: str = None, user_id: str = None,
                              limit: int = 100) -> List[Tuple]:
        """Retrieve attendance records with optional filters"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()

            query = 'SELECT * FROM attendance'
            params = []
            conditions = []

            if date:
                conditions.append('date = ?')
                params.append(date)

            if user_id:
                conditions.append('user_id = ?')
                params.append(user_id)

            if conditions:
                query += ' WHERE ' + ' AND '.join(conditions)

            query += ' ORDER BY timestamp DESC LIMIT ?'
            params.append(limit)

            cursor.execute(query, params)
            records = cursor.fetchall()

            conn.close()
            return records

        except Exception as e:
            print(f"✗ Record retrieval error: {e}")
            return []

    def get_user_info(self, user_id: str) -> Optional[Tuple]:
        """Get user information"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()

            cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            user = cursor.fetchone()

            conn.close()
            return user

        except Exception as e:
            print(f"✗ User info error: {e}")
            return None

    def get_user_by_regno(self, registration_number: str) -> Optional[Tuple]:
        """Get user by registration number"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()

            cursor.execute('SELECT * FROM users WHERE registration_number = ?',
                          (registration_number,))
            user = cursor.fetchone()

            conn.close()
            return user

        except Exception as e:
            print(f"✗ User lookup error: {e}")
            return None

    def get_all_users(self, active_only: bool = True) -> List[Tuple]:
        """Get all registered users"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()

            if active_only:
                cursor.execute('SELECT * FROM users WHERE is_active = 1 ORDER BY name')
            else:
                cursor.execute('SELECT * FROM users ORDER BY name')

            users = cursor.fetchall()
            conn.close()

            return users

        except Exception as e:
            print(f"✗ User list error: {e}")
            return []

    def delete_user_permanently(self, user_id: str) -> bool:
        """Permanently delete user (admin only)"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()

            # Delete user
            cursor.execute('DELETE FROM users WHERE user_id = ?', (user_id,))

            conn.commit()
            deleted = cursor.rowcount > 0
            conn.close()

            if deleted:
                print(f"✓ User {user_id} deleted permanently")
            return deleted

        except Exception as e:
            print(f"✗ User deletion error: {e}")
            return False

    def get_analytics_summary(self, date: str = None) -> Tuple:
        """Get analytics summary for a date or overall"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()

            if date:
                cursor.execute('''
                    SELECT 
                        COUNT(*) as total,
                        AVG(engagement_score) as avg_engagement,
                        AVG(liveness_score) as avg_liveness,
                        AVG(confidence) as avg_confidence
                    FROM attendance 
                    WHERE date = ?
                ''', (date,))
            else:
                cursor.execute('''
                    SELECT 
                        COUNT(*) as total,
                        AVG(engagement_score) as avg_engagement,
                        AVG(liveness_score) as avg_liveness,
                        AVG(confidence) as avg_confidence
                    FROM attendance
                ''')

            result = cursor.fetchone()
            conn.close()

            return result if result else (0, 0.0, 0.0, 0.0)

        except Exception as e:
            print(f"✗ Analytics error: {e}")
            return (0, 0.0, 0.0, 0.0)

    def get_user_attendance_history(self, user_id: str, limit: int = 30) -> List[Tuple]:
        """Get attendance history for specific user"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT date, time, liveness_score, emotion, engagement_score, confidence
                FROM attendance
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (user_id, limit))

            history = cursor.fetchall()
            conn.close()

            return history

        except Exception as e:
            print(f"✗ History retrieval error: {e}")
            return []

    def export_to_csv(self, output_file: str, date: str = None) -> bool:
        """Export attendance records to CSV"""
        try:
            import csv

            records = self.get_attendance_records(date=date, limit=10000)

            with open(output_file, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)

                # Header
                writer.writerow(['ID', 'UserID', 'Name', 'RegNo', 'Timestamp', 'Date', 'Time',
                               'Liveness', 'Emotion', 'Engagement', 'Confidence',
                               'BlockchainHash', 'Location'])

                # Data
                for record in records:
                    writer.writerow(record[:14])  # First 14 columns

            print(f"✓ Exported {len(records)} records to {output_file}")
            return True

        except Exception as e:
            print(f"✗ Export error: {e}")
            return False


# Test the database manager
if __name__ == "__main__":
    print("Testing Enhanced Database Manager\n")

    # Initialize database
    db = DatabaseManager("test_attendance.db")

    # Test add user with registration number
    test_encoding = np.random.rand(128)
    db.add_user("john_doe", "John Doe", test_encoding,
                registration_number="2021CS001",
                email="john@example.com",
                department="Computer Science")

    # Test get user by regno
    user = db.get_user_by_regno("2021CS001")
    if user:
        print(f"Found user: {user[1]} - {user[2]}")

    print("\n✓ Enhanced database testing complete")