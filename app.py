import math
import sqlite3
from datetime import date, datetime, timedelta

from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash

from database.db import (
    CATEGORIES,
    create_expense,
    create_user,
    get_category_totals,
    get_db,
    get_expense_summary,
    get_recent_expenses,
    get_user_by_email,
    get_user_by_id,
    init_db,
    seed_db,
)

app = Flask(__name__)
app.secret_key = "dev-secret-key-change-me"  # dev only; move to env config later

with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Helpers                                                             #
# ------------------------------------------------------------------ #

MAX_AMOUNT = 10_000_000
MAX_DESCRIPTION_LENGTH = 200
EXPENSE_FORM_FIELDS = ("amount", "category", "date", "description")


def _current_user_id():
    """Return the signed-in user's id, or None if logged out or the user is gone."""
    user_id = session.get("user_id")
    if user_id is None:
        return None
    if get_user_by_id(user_id) is None:
        session.clear()
        return None
    return user_id


def _validate_iso_date(value):
    """Return value as a canonical YYYY-MM-DD string, or None if empty/invalid.

    The canonical form matters: dates are compared as text in SQL.
    """
    try:
        return datetime.strptime(value, "%Y-%m-%d").strftime("%Y-%m-%d")
    except (TypeError, ValueError):
        return None


def _get_date_range():
    """Read the optional from/to query params as (date_from, date_to).

    Invalid values are ignored. If the range is reversed, flash an error and
    return (None, None) so the unfiltered data is shown.
    """
    date_from = _validate_iso_date(request.args.get("from", ""))
    date_to = _validate_iso_date(request.args.get("to", ""))
    if date_from and date_to and date_from > date_to:
        flash("Start date must be on or before end date", "error")
        return None, None
    return date_from, date_to


def _build_presets(today):
    """Return the quick-filter links shown above the profile stats."""
    ranges = [
        ("This month", today.replace(day=1).isoformat(), today.isoformat()),
        ("Last 30 days", (today - timedelta(days=30)).isoformat(), today.isoformat()),
    ]
    presets = [
        {
            "label": label,
            "url": url_for("profile", **{"from": start, "to": end}),
        }
        for label, start, end in ranges
    ]
    presets.append({"label": "All time", "url": url_for("profile")})
    return presets


def _parse_expense_form(form):
    """Validate the add-expense form and return (values, error).

    values is a dict ready for create_expense when error is None.
    """
    try:
        amount = float(form.get("amount", "").strip())
    except ValueError:
        return None, "Enter a valid amount"
    if not math.isfinite(amount) or amount <= 0:
        return None, "Amount must be greater than 0"
    if amount > MAX_AMOUNT:
        return None, f"Amount must be at most {MAX_AMOUNT:,}"

    category = form.get("category", "")
    if category not in CATEGORIES:
        return None, "Choose a valid category"

    expense_date = _validate_iso_date(form.get("date", "").strip())
    if expense_date is None:
        return None, "Enter a valid date"

    description = form.get("description", "").strip()[:MAX_DESCRIPTION_LENGTH] or None

    return {
        "amount": round(amount, 2),
        "category": category,
        "expense_date": expense_date,
        "description": description,
    }, None


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
        "member_since": datetime.strptime(
            row["created_at"], "%Y-%m-%d %H:%M:%S"
        ).strftime("%B %Y"),
    }

    date_from, date_to = _get_date_range()
    range_kwargs = {"date_from": date_from, "date_to": date_to}
    filters = {
        "date_from": date_from or "",
        "date_to": date_to or "",
        "active": bool(date_from or date_to),
    }
    presets = _build_presets(date.today())

    # ===== SECTION 1: TRANSACTIONS (subagent 1) =====
    transactions = [
        {
            "date": datetime.strptime(row["date"], "%Y-%m-%d").strftime("%d %b %Y"),
            "description": row["description"] or "",
            "category": row["category"],
            "amount": float(row["amount"]),
        }
        for row in get_recent_expenses(user_id, **range_kwargs)
    ]
    # ===== END SECTION 1 =====

    # ===== SECTION 2: SUMMARY (subagent 2) =====
    total, count, top = get_expense_summary(user_id, **range_kwargs)
    stats = {
        "total_spent": float(total or 0),
        "transaction_count": count,
        "top_category": top or "\u2014",
    }
    # ===== END SECTION 2 =====

    # ===== SECTION 3: CATEGORIES (subagent 3) =====
    category_rows = get_category_totals(user_id, **range_kwargs)
    grand_total = sum(float(row["total"]) for row in category_rows)
    categories = [
        {
            "name": row["category"],
            "total": float(row["total"]),
            "percent": (
                round(float(row["total"]) / grand_total * 100) if grand_total else 0
            ),
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
        filters=filters,
        presets=presets,
    )


@app.route("/analytics")
def analytics():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    return render_template("analytics.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #


@app.route("/expenses/add", methods=["GET", "POST"])
def add_expense():
    user_id = _current_user_id()
    if user_id is None:
        return redirect(url_for("login"))

    form = {
        "amount": "",
        "category": "",
        "date": date.today().isoformat(),
        "description": "",
    }

    if request.method == "POST":
        values, error = _parse_expense_form(request.form)
        if error is None:
            create_expense(user_id, **values)
            flash("Expense added", "success")
            return redirect(url_for("profile"))
        flash(error, "error")
        form = {key: request.form.get(key, "") for key in EXPENSE_FORM_FIELDS}

    return render_template(
        "add_expense.html",
        categories=CATEGORIES,
        form=form,
        max_amount=MAX_AMOUNT,
        max_description=MAX_DESCRIPTION_LENGTH,
    )


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
