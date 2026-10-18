import sqlite3

DATABASE = "expense_tracker.db"


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
    """Initialize database with schema."""
    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )

    db.commit()
    db.close()


# ------------------------------------------------------------------ #
# Database Seeding                                                   #
# ------------------------------------------------------------------ #

def seed_db():
    """Seed database with sample data for development."""
    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] > 0:
        db.close()
        return

    sample_users = [
        ("alice@example.com", "hashed_password_1"),
        ("bob@example.com", "hashed_password_2"),
    ]

    for email, password in sample_users:
        cursor.execute(
            "INSERT INTO users (email, password) VALUES (?, ?)",
            (email, password),
        )

    db.commit()

    cursor.execute("SELECT id FROM users LIMIT 1")
    user_id = cursor.fetchone()[0]

    sample_expenses = [
        (user_id, 50.00, "Food", "Lunch at cafe"),
        (user_id, 30.00, "Transport", "Gas for car"),
        (user_id, 100.00, "Entertainment", "Movie tickets"),
    ]

    for user_id, amount, category, description in sample_expenses:
        cursor.execute(
            """
            INSERT INTO expenses (user_id, amount, category, description)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, amount, category, description),
        )

    db.commit()
    db.close()
