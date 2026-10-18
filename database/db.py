import os
import sqlite3
from contextlib import closing
from datetime import date

from werkzeug.security import generate_password_hash

DATABASE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "expense_tracker.db",
)

CATEGORIES = [
    "Food",
    "Transport",
    "Bills",
    "Health",
    "Entertainment",
    "Shopping",
    "Other",
]


# ------------------------------------------------------------------ #
# Database Connection                                                #
# ------------------------------------------------------------------ #

def get_db():
    """Get database connection with row factory and foreign keys enabled."""
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


# ------------------------------------------------------------------ #
# Database Initialization                                            #
# ------------------------------------------------------------------ #

def init_db():
    """Create tables if they do not exist."""
    with closing(get_db()) as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now'))
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                date TEXT NOT NULL,
                description TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        )
        db.commit()


# ------------------------------------------------------------------ #
# Database Seeding                                                   #
# ------------------------------------------------------------------ #

def seed_db():
    """Insert a demo user and sample expenses once."""
    with closing(get_db()) as db:
        if db.execute("SELECT COUNT(*) FROM users").fetchone()[0] > 0:
            return

        cursor = db.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Demo User", "demo@spendly.com", generate_password_hash("demo123")),
        )
        user_id = cursor.lastrowid

        today = date.today()
        samples = [
            (450.00, "Food", 1, "Groceries"),
            (120.00, "Transport", 3, "Metro card recharge"),
            (1800.00, "Bills", 5, "Electricity bill"),
            (650.00, "Health", 8, "Pharmacy"),
            (900.00, "Entertainment", 12, "Movie and dinner"),
            (2200.00, "Shopping", 15, "New shoes"),
            (300.00, "Other", 18, "Gift wrapping and cards"),
            (220.00, "Food", 22, "Lunch with friends"),
        ]
        db.executemany(
            """
            INSERT INTO expenses (user_id, amount, category, date, description)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (user_id, amount, category, today.replace(day=day).isoformat(), desc)
                for amount, category, day, desc in samples
            ],
        )
        db.commit()
