# Spec: Backend Routes For Profile Page

## Overview
This feature replaces the hardcoded data in the `/profile` view with real queries against the SQLite database. Step 4 built the complete profile UI (user card, summary stats, transaction table, category breakdown) using static Python dicts; this step wires each of those sections to the logged-in user's actual `users` and `expenses` rows. The template and CSS stay as they are — only the data source changes — so the page now reflects whoever is signed in, including brand-new users with no expenses.

## Depends on
- Step 1: Database setup (`users` and `expenses` tables, `get_db()`)
- Step 2: Registration (accounts exist to look up)
- Step 3: Login + Logout (`session["user_id"]` is set)
- Step 4: Profile page design (`templates/profile.html` and its context shape)

## Routes
- `GET /profile` — render the profile page using database data for the signed-in user — logged-in only (redirect to `/login` if not authenticated; unchanged)

No other new routes.

## Database changes
No database changes. The existing `users` (`id`, `name`, `email`, `password_hash`, `created_at`) and `expenses` (`id`, `user_id`, `amount`, `category`, `date`, `description`, `created_at`) tables are sufficient.

New query helpers are added to `database/db.py` (all take `user_id`, use `get_db()` inside `closing(...)`, and use parameterised SQL):
- `get_user_by_id(user_id)` — returns the user row or `None`
- `get_expense_summary(user_id)` — returns total spent, transaction count, and top category (by total amount)
- `get_recent_expenses(user_id, limit=10)` — returns the user's expenses ordered by `date DESC, id DESC`
- `get_category_totals(user_id)` — returns `(category, total)` rows ordered by total descending

## Templates
- **Create:** none
- **Modify:** `templates/profile.html` — only if needed to render the empty state (see below); the context variable names (`user`, `stats`, `transactions`, `categories`) and their keys must not change:
  - `user`: `name`, `email`, `initials`, `member_since`
  - `stats`: `total_spent`, `transaction_count`, `top_category`
  - `transactions`: list of `date`, `description`, `category`, `amount`
  - `categories`: list of `name`, `total`, `percent`
  - When the user has no expenses, show a short "No expenses yet" message in the transactions and category panels instead of empty tables, and show `—` for top category

## Files to change
- `app.py` — in `profile()`: load the user via `get_user_by_id`; if the row is missing (stale session), `session.clear()` and redirect to `/login`; build `user`, `stats`, `transactions`, `categories` from the new helpers; delete all hardcoded dicts/lists
- `database/db.py` — add the four helper functions above
- `templates/profile.html` — empty-state handling only (see Templates)
- `static/css/style.css` — only if the empty-state message needs a class; use existing CSS variables

## Files to create
- `tests/test_profile.py` — pytest tests covering the definition of done (uses a temporary database, not `expense_tracker.db`)
- `tests/conftest.py` — app/client fixtures that point `database.db.DATABASE` at a temp file

## New dependencies
No new dependencies (`pytest` and `pytest-flask` are already in `requirements.txt`).

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only — never string-format SQL
- Passwords hashed with werkzeug (no changes to auth in this step)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- No inline styles
- Every query must filter by `user_id = ?` using `session["user_id"]` — a user must never see another user's expenses
- Do all aggregation in SQL (`SUM`, `COUNT`, `GROUP BY`), not in Python loops over all rows
- Format values in the view to match the Step 4 shapes: `date` as `"%d %b %Y"` (e.g. `22 Oct 2026`), `member_since` as `"%B %Y"` from `users.created_at`, `initials` from the first letters of up to two words of `name` (uppercased), `amount`/`total` as floats
- `percent` is each category's share of total spent as a whole number; guard against division by zero when there are no expenses
- Category badge and progress-bar classes continue to derive from the category name; do not add inline colour styles
- Do not implement add/edit/delete expense routes in this step (Steps 7–9)

## Definition of done
- [ ] Visiting `/profile` while logged out still redirects to `/login`
- [ ] Logging in as `demo@spendly.com` / `demo123` shows the page with the 8 seeded expenses, total ₹6,640.00, 8 transactions, and top category Shopping
- [ ] The transaction table is ordered newest first and shows dates formatted like `22 Oct 2026`
- [ ] The category breakdown lists each category the user has spent in, ordered by total descending, with percentages that match each category's share of the total
- [ ] Registering a new account and logging in shows that user's own name, email, initials and member-since month — not "Demo User"
- [ ] A new user with no expenses sees `₹0.00`, `0` transactions, `—` as top category, and "No expenses yet" messages; the page returns HTTP 200 with no error
- [ ] Adding a row directly to the `expenses` table for the demo user (via sqlite3) shows up on the next page load
- [ ] A user never sees another user's expenses (verified with two accounts)
- [ ] If the logged-in user's row is deleted from the database, `/profile` clears the session and redirects to `/login` instead of erroring
- [ ] No hardcoded transaction/category data remains in `app.py`
- [ ] No hex colour values appear in `profile.html`
- [ ] `pytest tests/test_profile.py` passes
