# Spec: Profile Page Design

## Overview
Replace the "coming in Step 4" placeholder at `/profile` with a real, designed profile page for the signed-in user. The page shows who the user is (name, email, member-since date), a short summary of their spending (total spent, number of expenses, top category), a per-category breakdown, and a list of their recent expenses. This is the landing page after login, so it gives the user a first view of their own data before the add/edit/delete features arrive in Steps 7–9. The page is read-only and visually consistent with the existing auth pages and landing page.

## Depends on
- Step 01 — Database setup (`users` and `expenses` tables, `get_db()`, seeded demo data)
- Step 02 — Registration (users exist, `create_user()`)
- Step 03 — Login and Logout (`session["user_id"]`, session-aware navbar, `profile.html` placeholder)

## Routes
- `GET /profile` — render the profile page for the user in `session["user_id"]`; redirect to `/login` if no one is signed in — logged-in (already exists as a placeholder, upgrade it)

No other new routes.

## Database changes
No new tables or columns. The existing `users` (`id`, `name`, `email`, `created_at`) and `expenses` (`user_id`, `amount`, `category`, `date`, `description`) tables hold everything needed.

New read-only helpers must be added to `database/db.py` (all parameterised, all scoped by `user_id`):
- `get_user_by_id(user_id)` — returns the `users` row as `sqlite3.Row`, or `None`
- `get_expense_summary(user_id)` — returns `total` (sum of amounts, `0` when none) and `count` of the user's expenses
- `get_category_totals(user_id)` — returns rows of `category` and `total`, ordered by `total` descending
- `get_recent_expenses(user_id, limit=10)` — returns the user's most recent expenses ordered by `date` descending, then `id` descending

## Templates
- **Modify:** `templates/profile.html`
  - Replace the placeholder with the full profile layout, still extending `base.html`
  - **Header card:** avatar circle with the user's initial, name, email, and "Member since <Month YYYY>"
  - **Summary row:** three stat cards — Total spent, Number of expenses, Top category
  - **Category breakdown:** one row per category with name, amount and a proportional bar
  - **Recent expenses:** table of date, description, category and amount, newest first
  - **Empty state:** when the user has no expenses, hide the breakdown and table and show a friendly message instead; stat cards show zero and "—"
  - Amounts are formatted with the rupee sign and two decimals (e.g. `₹1,800.00`)
  - Responsive: stat cards and layout stack on narrow screens
- **Modify:** `templates/base.html`
  - Add a "Profile" link to the navbar, shown only when signed in, pointing to `url_for('profile')`

## Files to change
- `app.py` — upgrade `profile()` to require login, load data via the new helpers and pass it to the template; import the new helpers
- `database/db.py` — add the four read-only helpers
- `templates/profile.html` — full profile design
- `templates/base.html` — "Profile" nav link when signed in
- `static/css/style.css` — profile page styles (new section, using existing CSS variables)

## Files to create
None.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only — never use f-strings in SQL
- Passwords hashed with werkzeug (no password handling is added in this step; never read or display `password_hash` on the page)
- Use CSS variables — never hardcode hex values; reuse the variables already defined in `:root` and add new ones there only if truly needed
- All templates extend `base.html`
- Use `url_for()` for every internal link — never hardcode URLs
- Every query must filter by the `user_id` from the session so a user can only ever see their own data
- If `session["user_id"]` is missing, redirect to `url_for('login')`; if it points to a user that no longer exists, call `session.clear()` and redirect to `url_for('login')`
- Do all aggregation in SQL (`SUM`, `COUNT`, `GROUP BY`) rather than looping in Python or Jinja
- Format amounts and dates in the template or a small Jinja filter — do not store formatted strings in the database
- Keep the page read-only: no add, edit or delete links or buttons (Steps 7–9)
- Do not add route-protection decorators for other routes, filters, date-range pickers or charts libraries — out of scope
- Follow the existing visual language (DM Serif Display headings, DM Sans body, `--radius-*` and `--border` tokens)

## Definition of done
- [ ] Visiting `/profile` while signed out redirects to `/login`
- [ ] Signing in as `demo@spendly.com` / `demo123` lands on `/profile` showing "Demo User" and `demo@spendly.com`
- [ ] The header card shows the avatar initial and a "Member since" month and year
- [ ] The three stat cards show the correct total, expense count and top category for the demo user (total ₹6,640.00, 8 expenses, top category Shopping)
- [ ] The category breakdown lists categories from highest to lowest total, with bars proportional to the amounts
- [ ] The recent expenses table lists the user's expenses newest first, with date, description, category and ₹ amount
- [ ] A newly registered user with no expenses sees zeros, "—" for top category, and the empty-state message instead of the table
- [ ] A second user never sees the demo user's expenses
- [ ] The navbar shows a "Profile" link only while signed in, and it opens `/profile`
- [ ] The layout is usable at phone width (stat cards stack, table does not overflow the page)
- [ ] `grep -nE '#[0-9a-fA-F]{3,6}' ` on the new profile CSS block finds no hardcoded hex values
- [ ] No add, edit or delete controls appear on the page
- [ ] The app starts with `python3 app.py` and `pytest` still passes
