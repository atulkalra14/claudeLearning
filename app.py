import sqlite3

from flask import (
    Flask, abort, flash, redirect, render_template, request, session, url_for,
)
from werkzeug.security import check_password_hash

from database.db import create_user, get_db, get_user_by_email, init_db, seed_db

app = Flask(__name__)
app.secret_key = "dev-secret-key-change-me"  # dev only; move to env config later

with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    if session.get("user_id"):
        return redirect(url_for("profile"))
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("profile"))
    if request.method == "GET":
        return render_template("register.html")
    if request.method != "POST":
        abort(405)

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")

    error = None
    if not (name and email and password and confirm_password):
        error = "All fields are required"
    elif len(password) < 8:
        error = "Password must be at least 8 characters"
    elif password != confirm_password:
        error = "Passwords do not match"
    else:
        try:
            create_user(name, email, password)
        except sqlite3.IntegrityError:
            error = "Email already registered"

    if error:
        flash(error, "error")
        return render_template("register.html", name=name, email=email)

    flash("Account created! Please sign in.", "success")
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("profile"))
    if request.method == "GET":
        return render_template("login.html")
    if request.method != "POST":
        abort(405)

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    error = None
    if not (email and password):
        error = "All fields are required"
    else:
        user = get_user_by_email(email)
        if user is None or not check_password_hash(user["password_hash"], password):
            error = "Invalid email or password"

    if error:
        flash(error, "error")
        return render_template("login.html", email=email)

    session["user_id"] = user["id"]
    return redirect(url_for("profile"))


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been signed out.", "success")
    return redirect(url_for("landing"))


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    # Hardcoded UI data — real queries are wired up in Step 5.
    user = {
        "name": "Demo User",
        "email": "demo@spendly.com",
        "initials": "DU",
        "member_since": "January 2026",
    }
    stats = {
        "total_spent": 6640.00,
        "transaction_count": 8,
        "top_category": "Shopping",
    }
    transactions = [
        {"date": "22 Oct 2026", "description": "Lunch with friends", "category": "Food", "amount": 220.00},
        {"date": "18 Oct 2026", "description": "Gift wrapping and cards", "category": "Other", "amount": 300.00},
        {"date": "15 Oct 2026", "description": "New shoes", "category": "Shopping", "amount": 2200.00},
        {"date": "12 Oct 2026", "description": "Movie and dinner", "category": "Entertainment", "amount": 900.00},
        {"date": "08 Oct 2026", "description": "Pharmacy", "category": "Health", "amount": 650.00},
        {"date": "05 Oct 2026", "description": "Electricity bill", "category": "Bills", "amount": 1800.00},
        {"date": "03 Oct 2026", "description": "Metro card recharge", "category": "Transport", "amount": 120.00},
        {"date": "01 Oct 2026", "description": "Groceries", "category": "Food", "amount": 450.00},
    ]
    categories = [
        {"name": "Shopping", "total": 2200.00, "percent": 33},
        {"name": "Bills", "total": 1800.00, "percent": 27},
        {"name": "Entertainment", "total": 900.00, "percent": 14},
        {"name": "Food", "total": 670.00, "percent": 10},
        {"name": "Health", "total": 650.00, "percent": 10},
        {"name": "Other", "total": 300.00, "percent": 5},
        {"name": "Transport", "total": 120.00, "percent": 2},
    ]
    return render_template(
        "profile.html",
        user=user,
        stats=stats,
        transactions=transactions,
        categories=categories,
    )


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
