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
        db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now'))
            )
            """)
        db.execute("""
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
            """)
        db.commit()


# ------------------------------------------------------------------ #
# Users                                                              #
# ------------------------------------------------------------------ #


def create_user(name, email, password):
    """Insert a new user with a hashed password and return the new id.

    Raises sqlite3.IntegrityError if the email is already registered.
    """
    with closing(get_db()) as db:
        cursor = db.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, generate_password_hash(password)),
        )
        db.commit()
        return cursor.lastrowid


def get_user_by_email(email):
    """Return the user row matching email, or None if there is no match."""
    with closing(get_db()) as db:
        return db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()


def get_user_by_id(user_id):
    """Return the user row matching id, or None if there is no match."""
    with closing(get_db()) as db:
        return db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


# ------------------------------------------------------------------ #
# Expenses                                                           #
# ------------------------------------------------------------------ #


def _date_clause(date_from, date_to):
    """Return (sql_fragment, params) for an optional inclusive date range.

    Dates are ISO YYYY-MM-DD strings. Only fixed SQL fragments are returned;
    the values themselves always travel as bound parameters.
    """
    clause = ""
    params = []
    if date_from:
        clause += " AND date >= ?"
        params.append(date_from)
    if date_to:
        clause += " AND date <= ?"
        params.append(date_to)
    return clause, params


def create_expense(user_id, amount, category, expense_date, description):
    """Insert an expense for the user and return the new id."""
    with closing(get_db()) as db:
        cursor = db.execute(
            """
            INSERT INTO expenses (user_id, amount, category, date, description)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, amount, category, expense_date, description),
        )
        db.commit()
        return cursor.lastrowid


def get_expense(user_id, expense_id):
    """Return the expense row if it belongs to the user, else None."""
    with closing(get_db()) as db:
        return db.execute(
            """
            SELECT id, amount, category, date, description
            FROM expenses
            WHERE id = ? AND user_id = ?
            """,
            (expense_id, user_id),
        ).fetchone()


def update_expense(user_id, expense_id, amount, category, expense_date, description):
    """Update the user's expense and return True if a row was changed.

    Returns False when the expense does not exist or belongs to someone else.
    """
    with closing(get_db()) as db:
        cursor = db.execute(
            """
            UPDATE expenses
            SET amount = ?, category = ?, date = ?, description = ?
            WHERE id = ? AND user_id = ?
            """,
            (amount, category, expense_date, description, expense_id, user_id),
        )
        db.commit()
        return cursor.rowcount == 1


def delete_expense(user_id, expense_id):
    """Delete the user's expense and return True if a row was removed.

    Returns False when the expense does not exist or belongs to someone else.
    """
    with closing(get_db()) as db:
        cursor = db.execute(
            "DELETE FROM expenses WHERE id = ? AND user_id = ?",
            (expense_id, user_id),
        )
        db.commit()
        return cursor.rowcount == 1


def get_recent_expenses(user_id, limit=10, date_from=None, date_to=None):
    """Return the user's most recent expenses, newest first.

    date_from and date_to optionally restrict the range (inclusive).
    """
    clause, params = _date_clause(date_from, date_to)
    with closing(get_db()) as db:
        return db.execute(
            f"""
            SELECT id, date, description, category, amount
            FROM expenses
            WHERE user_id = ?{clause}
            ORDER BY date DESC, id DESC
            LIMIT ?
            """,
            (user_id, *params, limit),
        ).fetchall()


def get_expense_summary(user_id, date_from=None, date_to=None):
    """Return (total_spent, transaction_count, top_category) for the user.

    total_spent is 0 and top_category is None when there are no expenses.
    date_from and date_to optionally restrict the range (inclusive).
    """
    clause, params = _date_clause(date_from, date_to)
    with closing(get_db()) as db:
        total, count = db.execute(
            f"""
            SELECT COALESCE(SUM(amount), 0), COUNT(*)
            FROM expenses
            WHERE user_id = ?{clause}
            """,
            (user_id, *params),
        ).fetchone()
        top = db.execute(
            f"""
            SELECT category
            FROM expenses
            WHERE user_id = ?{clause}
            GROUP BY category
            ORDER BY SUM(amount) DESC
            LIMIT 1
            """,
            (user_id, *params),
        ).fetchone()
        return total, count, top["category"] if top else None


def get_category_totals(user_id, date_from=None, date_to=None):
    """Return (category, total) rows for the user, largest total first.

    date_from and date_to optionally restrict the range (inclusive).
    """
    clause, params = _date_clause(date_from, date_to)
    with closing(get_db()) as db:
        return db.execute(
            f"""
            SELECT category, SUM(amount) AS total
            FROM expenses
            WHERE user_id = ?{clause}
            GROUP BY category
            ORDER BY total DESC
            """,
            (user_id, *params),
        ).fetchall()


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
