import sqlite3
from datetime import datetime

from flask import (
    Flask, abort, flash, redirect, render_template, request, session, url_for,
)
from werkzeug.security import check_password_hash

from database.db import (
    create_user, get_category_totals, get_db, get_expense_summary,
    get_recent_expenses, get_user_by_email, get_user_by_id, init_db, seed_db,
)

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


@app.route("/profile")
def profile():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    row = get_user_by_id(user_id)
    if row is None:
        session.clear()
        return redirect(url_for("login"))

    user = {
        "name": row["name"],
        "email": row["email"],
        "initials": "".join(w[0] for w in row["name"].split()[:2]).upper(),
        "member_since": datetime.strptime(row["created_at"], "%Y-%m-%d %H:%M:%S").strftime("%B %Y"),
    }

    # ===== SECTION 1: TRANSACTIONS (subagent 1) =====
    transactions = [
        {
            "date": datetime.strptime(row["date"], "%Y-%m-%d").strftime("%d %b %Y"),
            "description": row["description"] or "",
            "category": row["category"],
            "amount": float(row["amount"]),
        }
        for row in get_recent_expenses(user_id)
    ]
    # ===== END SECTION 1 =====

    # ===== SECTION 2: SUMMARY (subagent 2) =====
    total, count, top = get_expense_summary(user_id)
    stats = {
        "total_spent": float(total or 0),
        "transaction_count": count,
        "top_category": top or "\u2014",
    }
    # ===== END SECTION 2 =====

    # ===== SECTION 3: CATEGORIES (subagent 3) =====
    category_rows = get_category_totals(user_id)
    grand_total = sum(float(row["total"]) for row in category_rows)
    categories = [
        {
            "name": row["category"],
            "total": float(row["total"]),
            "percent": round(float(row["total"]) / grand_total * 100) if grand_total else 0,
        }
        for row in category_rows
    ]
    # ===== END SECTION 3 =====

    return render_template(
        "profile.html",
        user=user,
        stats=stats,
        transactions=transactions,
        categories=categories,
    )


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #


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
