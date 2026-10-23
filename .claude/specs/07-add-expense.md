# Spec: Add Expense

## Overview
This feature lets a signed-in user record a new expense through a form at `/expenses/add`. Until now the app only displays seeded data on the profile page; this step is the first one that writes expense rows. The form collects amount, category, date and an optional description, validates them on the server, inserts the row for the current user, and redirects back to `/profile` where the new expense appears in the transactions table, summary stats and category breakdown.

## Depends on
- Step 1: Database setup (`expenses` table, `CATEGORIES` list in `database/db.py`)
- Step 3: Login + Logout (`session["user_id"]`)
- Step 4/5: Profile page and its data helpers (the page the user is redirected to)
- Step 6: Date filter (`_validate_iso_date` helper in `app.py` is reused for date validation)

## Routes
- `GET /expenses/add` — render the empty add-expense form — logged-in only (redirect to `/login` if not authenticated)
- `POST /expenses/add` — validate the form, insert the expense for `session["user_id"]`, flash a success message and redirect to `/profile`; on validation error re-render the form with the entered values and a flashed error — logged-in only

The existing placeholder `add_expense()` in `app.py` is replaced (it currently only accepts GET and returns plain text). The edit and delete placeholders are left untouched.

## Database changes
No database changes. The existing `expenses` table (`user_id`, `amount`, `category`, `date`, `description`, `created_at`) already fits.

Add one new helper to `database/db.py` in the Expenses section:
- `create_expense(user_id, amount, category, expense_date, description)` — inserts a row using a parameterised query, commits, and returns the new row id. Uses `closing(get_db())` like the other helpers.

## Templates
- **Create:** `templates/add_expense.html` — extends `base.html`; a `POST` form to `url_for('add_expense')` with:
  - `amount` (`type="number"`, `step="0.01"`, `min="0.01"`, required)
  - `category` (`<select>` populated from the `categories` context list, required)
  - `date` (`type="date"`, required, defaults to today)
  - `description` (`type="text"`, optional, `maxlength="200"`)
  - Submit button and a "Cancel" link to `url_for('profile')`
  - Flashed messages rendered the same way as `register.html`
  - Entered values are re-filled after a validation error
- **Modify:** `templates/profile.html` — add an "Add expense" link/button pointing to `url_for('add_expense')`, and show a flashed success message after redirect if the template does not already render flashes
- **Modify (if needed):** `templates/base.html` — only if a navbar link to add-expense is wanted for logged-in users; keep the change minimal

## Files to change
- `app.py` — import `create_expense` and `CATEGORIES`; replace the `add_expense` placeholder with a GET/POST route
- `database/db.py` — add `create_expense`
- `templates/profile.html` — "Add expense" entry point and flash display
- `static/css/style.css` — any styles for the new form/button, using existing CSS variables and existing `.form-group` / `.form-input` classes where possible

## Files to create
- `templates/add_expense.html`
- `tests/test_07_add_expense.py`

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only — never build SQL from form values
- Passwords hashed with werkzeug (no auth changes in this step)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- No inline styles
- The user id must come from `session["user_id"]`, never from the form
- Redirect to `/login` when logged out, for both GET and POST (the POST must not insert anything)
- Server-side validation (do not rely on HTML attributes alone):
  - `amount` must parse as a number, be greater than 0, be finite (reject `nan`/`inf`), and be at most 10,000,000; round to 2 decimals
  - `category` must be one of `CATEGORIES`
  - `date` must pass `_validate_iso_date`; reject empty or malformed values
  - `description` is trimmed; empty becomes `None`/empty string; cap at 200 characters
- Invalid input must return HTTP 200 with a flashed error and re-filled fields, never a 500
- Rely on Jinja autoescaping for the re-filled description; do not use `|safe`
- Follow the existing view style: flash with categories `"error"` / `"success"`, use `url_for()` for all links and redirects
- Do not implement edit or delete (Steps 8–9) and do not change the profile data helpers

## Definition of done
- [ ] Logged out, `GET /expenses/add` redirects to `/login`; logged out `POST /expenses/add` redirects to `/login` and inserts nothing
- [ ] Logged in, `GET /expenses/add` returns 200 with amount, category, date and description fields; the category dropdown lists all 7 categories and the date defaults to today
- [ ] Submitting valid data (e.g. 250.50, Food, today, "Lunch") redirects to `/profile`, shows a success message, and the expense appears at the top of the transactions table
- [ ] After adding, the profile total, transaction count and category breakdown reflect the new expense
- [ ] The description can be left blank and the expense is still saved
- [ ] Missing amount, amount `0`, negative amount, and non-numeric amount each show an error and save nothing
- [ ] `nan` and `inf` amounts are rejected without a 500
- [ ] An invalid category (e.g. tampered form value) shows an error and saves nothing
- [ ] Missing or malformed date shows an error and saves nothing
- [ ] After a validation error the previously entered values are still in the form
- [ ] A description containing `<script>` is displayed escaped on the profile page
- [ ] The new row is stored with the logged-in user's id; a second account does not see it
- [ ] "Add expense" link on the profile page opens the form; "Cancel" returns to `/profile`
- [ ] No hex colour values added to templates or inline styles
- [ ] `pytest tests/test_07_add_expense.py` passes
