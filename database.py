"""
Database models and operations for Commission Tracker Bot
"""

import sqlite3
from datetime import datetime, timezone
from typing import Optional, List, Dict, Tuple
from decimal import Decimal
import config


class Database:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or config.DATABASE_PATH
        self.init_database()

    def get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_database(self):
        """Initialize database schema"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                name TEXT,
                timezone TEXT DEFAULT 'Africa/Nairobi',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Commissions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS commissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount NUMERIC NOT NULL,
                note TEXT,
                date_added TIMESTAMP NOT NULL,
                month TEXT NOT NULL,
                year INTEGER NOT NULL,
                split_user NUMERIC NOT NULL,
                split_partner NUMERIC NOT NULL,
                locked BOOLEAN DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)

        # Payouts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS payouts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount NUMERIC NOT NULL,
                date_paid TIMESTAMP NOT NULL,
                month TEXT NOT NULL,
                year INTEGER NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)

        # Monthly summaries table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS monthly_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                month TEXT NOT NULL,
                year INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                total_commission NUMERIC NOT NULL,
                split_user NUMERIC NOT NULL,
                split_partner NUMERIC NOT NULL,
                statement_id TEXT UNIQUE NOT NULL,
                closed BOOLEAN DEFAULT 0,
                generated_at TIMESTAMP NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                UNIQUE(user_id, month, year)
            )
        """)

        # Audit logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action_type TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                target_id INTEGER,
                before_value TEXT,
                after_value TEXT,
                timestamp TIMESTAMP NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)

        # Authorized users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS authorized_users (
                user_id INTEGER PRIMARY KEY,
                authorized_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                authorized_by INTEGER,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)

        # Pending authorizations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pending_authorizations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT,
                full_name TEXT,
                requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)

        conn.commit()
        conn.close()

    def get_or_create_user(self, user_id: int, name: str = None) -> Dict:
        """Get or create user"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()

        if not user:
            cursor.execute(
                "INSERT INTO users (user_id, name) VALUES (?, ?)",
                (user_id, name or f"User_{user_id}"),
            )
            conn.commit()
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            user = cursor.fetchone()

        conn.close()
        return dict(user) if user else None

    def get_all_users(self) -> List[Dict]:
        """Get all users"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def clear_database(self) -> bool:
        """Clear all data from database (keeps schema)"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # Delete all data from all tables
            cursor.execute("DELETE FROM audit_logs")
            cursor.execute("DELETE FROM monthly_summaries")
            cursor.execute("DELETE FROM payouts")
            cursor.execute("DELETE FROM commissions")
            cursor.execute("DELETE FROM pending_authorizations")
            cursor.execute("DELETE FROM authorized_users")
            cursor.execute("DELETE FROM users")
            
            # Reset auto-increment counters
            cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('commissions', 'payouts', 'monthly_summaries', 'audit_logs', 'pending_authorizations')")
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            conn.rollback()
            conn.close()
            raise e

    def is_authorized(self, user_id: int) -> bool:
        """Check if user is authorized"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM authorized_users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        return result is not None

    def add_pending_authorization(self, user_id: int, username: str | None = None, full_name: str | None = None) -> int:
        """Add pending authorization request"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Check if already pending
        cursor.execute("SELECT * FROM pending_authorizations WHERE user_id = ?", (user_id,))
        existing = cursor.fetchone()

        if existing:
            conn.close()
            return existing['id']

        cursor.execute("""
            INSERT INTO pending_authorizations (user_id, username, full_name)
            VALUES (?, ?, ?)
        """, (user_id, username, full_name))

        request_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return request_id

    def get_pending_authorizations(self) -> List[Dict]:
        """Get all pending authorization requests"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM pending_authorizations 
            ORDER BY requested_at DESC
        """)
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def clear_database(self) -> bool:
        """Clear all data from database (keeps schema)"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # Delete all data from all tables
            cursor.execute("DELETE FROM audit_logs")
            cursor.execute("DELETE FROM monthly_summaries")
            cursor.execute("DELETE FROM payouts")
            cursor.execute("DELETE FROM commissions")
            cursor.execute("DELETE FROM pending_authorizations")
            cursor.execute("DELETE FROM authorized_users")
            cursor.execute("DELETE FROM users")
            
            # Reset auto-increment counters
            cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('commissions', 'payouts', 'monthly_summaries', 'audit_logs', 'pending_authorizations')")
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            conn.rollback()
            conn.close()
            raise e

    def approve_user(self, user_id: int, authorized_by: int) -> bool:
        """Approve user authorization"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Check if already authorized
        if self.is_authorized(user_id):
            conn.close()
            return False

        # Add to authorized users
        cursor.execute("""
            INSERT INTO authorized_users (user_id, authorized_by)
            VALUES (?, ?)
        """, (user_id, authorized_by))

        # Remove from pending
        cursor.execute("DELETE FROM pending_authorizations WHERE user_id = ?", (user_id,))

        conn.commit()
        conn.close()
        return True

    def revoke_user(self, user_id: int) -> bool:
        """Revoke user authorization"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM authorized_users WHERE user_id = ?", (user_id,))
        deleted = cursor.rowcount > 0

        conn.commit()
        conn.close()
        return deleted

    def get_authorized_users(self) -> List[Dict]:
        """Get all authorized users"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT au.user_id, au.authorized_at, u.name 
            FROM authorized_users au
            LEFT JOIN users u ON au.user_id = u.user_id
            ORDER BY au.authorized_at DESC
        """)
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def clear_database(self) -> bool:
        """Clear all data from database (keeps schema)"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # Delete all data from all tables
            cursor.execute("DELETE FROM audit_logs")
            cursor.execute("DELETE FROM monthly_summaries")
            cursor.execute("DELETE FROM payouts")
            cursor.execute("DELETE FROM commissions")
            cursor.execute("DELETE FROM pending_authorizations")
            cursor.execute("DELETE FROM authorized_users")
            cursor.execute("DELETE FROM users")
            
            # Reset auto-increment counters
            cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('commissions', 'payouts', 'monthly_summaries', 'audit_logs', 'pending_authorizations')")
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            conn.rollback()
            conn.close()
            raise e

    def add_commission(
        self,
        user_id: int,
        amount: Decimal,
        note: str = None,
        month: str = None,
        year: int = None,
        split_user: Decimal = None,
        split_partner: Decimal = None,
    ) -> int:
        """Add commission entry"""
        from utils import get_current_month_year

        if month is None or year is None:
            month, year = get_current_month_year()

        if split_user is None or split_partner is None:
            split_user = Decimal(str(amount * config.DEFAULT_SPLIT_USER))
            split_partner = Decimal(str(amount * config.DEFAULT_SPLIT_PARTNER))

        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO commissions 
            (user_id, amount, note, date_added, month, year, split_user, split_partner)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                user_id,
                str(amount),
                note,
                datetime.now(timezone.utc).isoformat(),
                month,
                year,
                str(split_user),
                str(split_partner),
            ),
        )

        commission_id = cursor.lastrowid

        # Log audit
        cursor.execute(
            """
            INSERT INTO audit_logs (action_type, user_id, target_id, after_value, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """,
            (
                "add",
                user_id,
                commission_id,
                f"amount={amount}, split_user={split_user}, split_partner={split_partner}",
                datetime.now(timezone.utc).isoformat(),
            ),
        )

        conn.commit()
        conn.close()
        return commission_id

    def get_last_commission(self, user_id: int) -> Optional[Dict]:
        """Get last commission entry"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT * FROM commissions 
            WHERE user_id = ? 
            ORDER BY date_added DESC 
            LIMIT 1
        """,
            (user_id,),
        )

        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def delete_commission(self, commission_id: int, user_id: int) -> bool:
        """Delete commission entry (undo)"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Get commission before deletion
        cursor.execute(
            "SELECT * FROM commissions WHERE id = ? AND user_id = ?",
            (commission_id, user_id),
        )
        commission = cursor.fetchone()

        if not commission:
            conn.close()
            return False

        # Log audit
        cursor.execute(
            """
            INSERT INTO audit_logs (action_type, user_id, target_id, before_value, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """,
            (
                "undo",
                user_id,
                commission_id,
                f"amount={commission['amount']}, split_user={commission['split_user']}, split_partner={commission['split_partner']}",
                datetime.now(timezone.utc).isoformat(),
            ),
        )

        cursor.execute(
            "DELETE FROM commissions WHERE id = ? AND user_id = ?",
            (commission_id, user_id),
        )
        conn.commit()
        conn.close()
        return True

    def get_commissions(
        self,
        user_id: int,
        month: str = None,
        year: int = None,
        include_locked: bool = True,
    ) -> List[Dict]:
        """Get commissions for user, optionally filtered by month/year"""
        conn = self.get_connection()
        cursor = conn.cursor()

        query = "SELECT * FROM commissions WHERE user_id = ?"
        params = [user_id]

        if month and year:
            query += " AND month = ? AND year = ?"
            params.extend([month, year])
        elif not include_locked:
            query += " AND locked = 0"

        query += " ORDER BY date_added DESC"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def clear_database(self) -> bool:
        """Clear all data from database (keeps schema)"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # Delete all data from all tables
            cursor.execute("DELETE FROM audit_logs")
            cursor.execute("DELETE FROM monthly_summaries")
            cursor.execute("DELETE FROM payouts")
            cursor.execute("DELETE FROM commissions")
            cursor.execute("DELETE FROM pending_authorizations")
            cursor.execute("DELETE FROM authorized_users")
            cursor.execute("DELETE FROM users")
            
            # Reset auto-increment counters
            cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('commissions', 'payouts', 'monthly_summaries', 'audit_logs', 'pending_authorizations')")
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            conn.rollback()
            conn.close()
            raise e

    def is_authorized(self, user_id: int) -> bool:
        """Check if user is authorized"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM authorized_users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        return result is not None

    def add_pending_authorization(self, user_id: int, username: str | None = None, full_name: str | None = None) -> int:
        """Add pending authorization request"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Check if already pending
        cursor.execute("SELECT * FROM pending_authorizations WHERE user_id = ?", (user_id,))
        existing = cursor.fetchone()

        if existing:
            conn.close()
            return existing['id']

        cursor.execute("""
            INSERT INTO pending_authorizations (user_id, username, full_name)
            VALUES (?, ?, ?)
        """, (user_id, username, full_name))

        request_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return request_id

    def get_pending_authorizations(self) -> List[Dict]:
        """Get all pending authorization requests"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM pending_authorizations 
            ORDER BY requested_at DESC
        """)
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def clear_database(self) -> bool:
        """Clear all data from database (keeps schema)"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # Delete all data from all tables
            cursor.execute("DELETE FROM audit_logs")
            cursor.execute("DELETE FROM monthly_summaries")
            cursor.execute("DELETE FROM payouts")
            cursor.execute("DELETE FROM commissions")
            cursor.execute("DELETE FROM pending_authorizations")
            cursor.execute("DELETE FROM authorized_users")
            cursor.execute("DELETE FROM users")
            
            # Reset auto-increment counters
            cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('commissions', 'payouts', 'monthly_summaries', 'audit_logs', 'pending_authorizations')")
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            conn.rollback()
            conn.close()
            raise e

    def approve_user(self, user_id: int, authorized_by: int) -> bool:
        """Approve user authorization"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Check if already authorized
        if self.is_authorized(user_id):
            conn.close()
            return False

        # Add to authorized users
        cursor.execute("""
            INSERT INTO authorized_users (user_id, authorized_by)
            VALUES (?, ?)
        """, (user_id, authorized_by))

        # Remove from pending
        cursor.execute("DELETE FROM pending_authorizations WHERE user_id = ?", (user_id,))

        conn.commit()
        conn.close()
        return True

    def revoke_user(self, user_id: int) -> bool:
        """Revoke user authorization"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM authorized_users WHERE user_id = ?", (user_id,))
        deleted = cursor.rowcount > 0

        conn.commit()
        conn.close()
        return deleted

    def get_authorized_users(self) -> List[Dict]:
        """Get all authorized users"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT au.user_id, au.authorized_at, u.name 
            FROM authorized_users au
            LEFT JOIN users u ON au.user_id = u.user_id
            ORDER BY au.authorized_at DESC
        """)
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def clear_database(self) -> bool:
        """Clear all data from database (keeps schema)"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # Delete all data from all tables
            cursor.execute("DELETE FROM audit_logs")
            cursor.execute("DELETE FROM monthly_summaries")
            cursor.execute("DELETE FROM payouts")
            cursor.execute("DELETE FROM commissions")
            cursor.execute("DELETE FROM pending_authorizations")
            cursor.execute("DELETE FROM authorized_users")
            cursor.execute("DELETE FROM users")
            
            # Reset auto-increment counters
            cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('commissions', 'payouts', 'monthly_summaries', 'audit_logs', 'pending_authorizations')")
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            conn.rollback()
            conn.close()
            raise e

    def add_payout(self, user_id: int, amount: Decimal, month: str, year: int) -> int:
        """Record payout to partner"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO payouts (user_id, amount, date_paid, month, year)
            VALUES (?, ?, ?, ?, ?)
        """,
            (user_id, str(amount), datetime.now(timezone.utc).isoformat(), month, year),
        )

        payout_id = cursor.lastrowid

        # Log audit
        cursor.execute(
            """
            INSERT INTO audit_logs (action_type, user_id, target_id, after_value, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """,
            (
                "payout",
                user_id,
                payout_id,
                f"amount={amount}, month={month}, year={year}",
                datetime.now(timezone.utc).isoformat(),
            ),
        )

        conn.commit()
        conn.close()
        return payout_id

    def get_payouts(
        self, user_id: int, month: str = None, year: int = None
    ) -> List[Dict]:
        """Get payouts for user"""
        conn = self.get_connection()
        cursor = conn.cursor()

        query = "SELECT * FROM payouts WHERE user_id = ?"
        params = [user_id]

        if month and year:
            query += " AND month = ? AND year = ?"
            params.extend([month, year])

        query += " ORDER BY date_paid DESC"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def clear_database(self) -> bool:
        """Clear all data from database (keeps schema)"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # Delete all data from all tables
            cursor.execute("DELETE FROM audit_logs")
            cursor.execute("DELETE FROM monthly_summaries")
            cursor.execute("DELETE FROM payouts")
            cursor.execute("DELETE FROM commissions")
            cursor.execute("DELETE FROM pending_authorizations")
            cursor.execute("DELETE FROM authorized_users")
            cursor.execute("DELETE FROM users")
            
            # Reset auto-increment counters
            cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('commissions', 'payouts', 'monthly_summaries', 'audit_logs', 'pending_authorizations')")
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            conn.rollback()
            conn.close()
            raise e

    def is_authorized(self, user_id: int) -> bool:
        """Check if user is authorized"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM authorized_users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        return result is not None

    def add_pending_authorization(self, user_id: int, username: str | None = None, full_name: str | None = None) -> int:
        """Add pending authorization request"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Check if already pending
        cursor.execute("SELECT * FROM pending_authorizations WHERE user_id = ?", (user_id,))
        existing = cursor.fetchone()

        if existing:
            conn.close()
            return existing['id']

        cursor.execute("""
            INSERT INTO pending_authorizations (user_id, username, full_name)
            VALUES (?, ?, ?)
        """, (user_id, username, full_name))

        request_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return request_id

    def get_pending_authorizations(self) -> List[Dict]:
        """Get all pending authorization requests"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM pending_authorizations 
            ORDER BY requested_at DESC
        """)
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def clear_database(self) -> bool:
        """Clear all data from database (keeps schema)"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # Delete all data from all tables
            cursor.execute("DELETE FROM audit_logs")
            cursor.execute("DELETE FROM monthly_summaries")
            cursor.execute("DELETE FROM payouts")
            cursor.execute("DELETE FROM commissions")
            cursor.execute("DELETE FROM pending_authorizations")
            cursor.execute("DELETE FROM authorized_users")
            cursor.execute("DELETE FROM users")
            
            # Reset auto-increment counters
            cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('commissions', 'payouts', 'monthly_summaries', 'audit_logs', 'pending_authorizations')")
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            conn.rollback()
            conn.close()
            raise e

    def approve_user(self, user_id: int, authorized_by: int) -> bool:
        """Approve user authorization"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Check if already authorized
        if self.is_authorized(user_id):
            conn.close()
            return False

        # Add to authorized users
        cursor.execute("""
            INSERT INTO authorized_users (user_id, authorized_by)
            VALUES (?, ?)
        """, (user_id, authorized_by))

        # Remove from pending
        cursor.execute("DELETE FROM pending_authorizations WHERE user_id = ?", (user_id,))

        conn.commit()
        conn.close()
        return True

    def revoke_user(self, user_id: int) -> bool:
        """Revoke user authorization"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM authorized_users WHERE user_id = ?", (user_id,))
        deleted = cursor.rowcount > 0

        conn.commit()
        conn.close()
        return deleted

    def get_authorized_users(self) -> List[Dict]:
        """Get all authorized users"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT au.user_id, au.authorized_at, u.name 
            FROM authorized_users au
            LEFT JOIN users u ON au.user_id = u.user_id
            ORDER BY au.authorized_at DESC
        """)
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def clear_database(self) -> bool:
        """Clear all data from database (keeps schema)"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # Delete all data from all tables
            cursor.execute("DELETE FROM audit_logs")
            cursor.execute("DELETE FROM monthly_summaries")
            cursor.execute("DELETE FROM payouts")
            cursor.execute("DELETE FROM commissions")
            cursor.execute("DELETE FROM pending_authorizations")
            cursor.execute("DELETE FROM authorized_users")
            cursor.execute("DELETE FROM users")
            
            # Reset auto-increment counters
            cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('commissions', 'payouts', 'monthly_summaries', 'audit_logs', 'pending_authorizations')")
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            conn.rollback()
            conn.close()
            raise e

    def close_month(self, user_id: int, month: str, year: int) -> str:
        """Close month and generate statement"""
        from utils import generate_statement_id
        from decimal import Decimal

        conn = self.get_connection()
        cursor = conn.cursor()

        # Calculate totals
        commissions = self.get_commissions(user_id, month, year)
        total_commission = sum(Decimal(c["amount"]) for c in commissions)
        split_user = sum(Decimal(c["split_user"]) for c in commissions)
        split_partner = sum(Decimal(c["split_partner"]) for c in commissions)

        statement_id = generate_statement_id(user_id, month, year)

        # Create or update summary
        cursor.execute(
            """
            INSERT OR REPLACE INTO monthly_summaries
            (user_id, month, year, total_commission, split_user, split_partner, statement_id, closed, generated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                user_id,
                month,
                year,
                str(total_commission),
                str(split_user),
                str(split_partner),
                statement_id,
                1,
                datetime.now(timezone.utc).isoformat(),
            ),
        )

        # Lock commissions
        cursor.execute(
            """
            UPDATE commissions 
            SET locked = 1 
            WHERE user_id = ? AND month = ? AND year = ?
        """,
            (user_id, month, year),
        )

        # Log audit
        cursor.execute(
            """
            INSERT INTO audit_logs (action_type, user_id, after_value, timestamp)
            VALUES (?, ?, ?, ?)
        """,
            (
                "month_close",
                user_id,
                f"month={month}, year={year}, statement_id={statement_id}",
                datetime.now(timezone.utc).isoformat(),
            ),
        )

        conn.commit()
        conn.close()
        return statement_id

    def get_monthly_summary(
        self, user_id: int, month: str, year: int
    ) -> Optional[Dict]:
        """Get monthly summary"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT * FROM monthly_summaries 
            WHERE user_id = ? AND month = ? AND year = ?
        """,
            (user_id, month, year),
        )

        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_all_monthly_summaries(self, user_id: int, year: int = None) -> List[Dict]:
        """Get all monthly summaries for user"""
        conn = self.get_connection()
        cursor = conn.cursor()

        if year:
            cursor.execute(
                """
                SELECT * FROM monthly_summaries 
                WHERE user_id = ? AND year = ?
                ORDER BY year DESC, month DESC
            """,
                (user_id, year),
            )
        else:
            cursor.execute(
                """
                SELECT * FROM monthly_summaries 
                WHERE user_id = ?
                ORDER BY year DESC, month DESC
            """,
                (user_id,),
            )

        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def clear_database(self) -> bool:
        """Clear all data from database (keeps schema)"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # Delete all data from all tables
            cursor.execute("DELETE FROM audit_logs")
            cursor.execute("DELETE FROM monthly_summaries")
            cursor.execute("DELETE FROM payouts")
            cursor.execute("DELETE FROM commissions")
            cursor.execute("DELETE FROM pending_authorizations")
            cursor.execute("DELETE FROM authorized_users")
            cursor.execute("DELETE FROM users")
            
            # Reset auto-increment counters
            cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('commissions', 'payouts', 'monthly_summaries', 'audit_logs', 'pending_authorizations')")
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            conn.rollback()
            conn.close()
            raise e

    def is_authorized(self, user_id: int) -> bool:
        """Check if user is authorized"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM authorized_users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        return result is not None

    def add_pending_authorization(self, user_id: int, username: str | None = None, full_name: str | None = None) -> int:
        """Add pending authorization request"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Check if already pending
        cursor.execute("SELECT * FROM pending_authorizations WHERE user_id = ?", (user_id,))
        existing = cursor.fetchone()

        if existing:
            conn.close()
            return existing['id']

        cursor.execute("""
            INSERT INTO pending_authorizations (user_id, username, full_name)
            VALUES (?, ?, ?)
        """, (user_id, username, full_name))

        request_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return request_id

    def get_pending_authorizations(self) -> List[Dict]:
        """Get all pending authorization requests"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM pending_authorizations 
            ORDER BY requested_at DESC
        """)
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def clear_database(self) -> bool:
        """Clear all data from database (keeps schema)"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # Delete all data from all tables
            cursor.execute("DELETE FROM audit_logs")
            cursor.execute("DELETE FROM monthly_summaries")
            cursor.execute("DELETE FROM payouts")
            cursor.execute("DELETE FROM commissions")
            cursor.execute("DELETE FROM pending_authorizations")
            cursor.execute("DELETE FROM authorized_users")
            cursor.execute("DELETE FROM users")
            
            # Reset auto-increment counters
            cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('commissions', 'payouts', 'monthly_summaries', 'audit_logs', 'pending_authorizations')")
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            conn.rollback()
            conn.close()
            raise e

    def approve_user(self, user_id: int, authorized_by: int) -> bool:
        """Approve user authorization"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Check if already authorized
        if self.is_authorized(user_id):
            conn.close()
            return False

        # Add to authorized users
        cursor.execute("""
            INSERT INTO authorized_users (user_id, authorized_by)
            VALUES (?, ?)
        """, (user_id, authorized_by))

        # Remove from pending
        cursor.execute("DELETE FROM pending_authorizations WHERE user_id = ?", (user_id,))

        conn.commit()
        conn.close()
        return True

    def revoke_user(self, user_id: int) -> bool:
        """Revoke user authorization"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM authorized_users WHERE user_id = ?", (user_id,))
        deleted = cursor.rowcount > 0

        conn.commit()
        conn.close()
        return deleted

    def get_authorized_users(self) -> List[Dict]:
        """Get all authorized users"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT au.user_id, au.authorized_at, u.name 
            FROM authorized_users au
            LEFT JOIN users u ON au.user_id = u.user_id
            ORDER BY au.authorized_at DESC
        """)
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def clear_database(self) -> bool:
        """Clear all data from database (keeps schema)"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # Delete all data from all tables
            cursor.execute("DELETE FROM audit_logs")
            cursor.execute("DELETE FROM monthly_summaries")
            cursor.execute("DELETE FROM payouts")
            cursor.execute("DELETE FROM commissions")
            cursor.execute("DELETE FROM pending_authorizations")
            cursor.execute("DELETE FROM authorized_users")
            cursor.execute("DELETE FROM users")
            
            # Reset auto-increment counters
            cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('commissions', 'payouts', 'monthly_summaries', 'audit_logs', 'pending_authorizations')")
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            conn.rollback()
            conn.close()
            raise e
