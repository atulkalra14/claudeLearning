# Spec: Date Filter Profile Page

## Overview
This feature adds a date-range filter to the `/profile` page. Step 5 wired the profile page to real database data, but every section (summary stats, transaction table, category breakdown) always covers the user's entire history. This step lets the signed-in user narrow all three sections to a chosen period via `from` and `to` query parameters, using a small filter form with quick presets (This month, Last 30 days, All time). Filtering is done in SQL so the stats, transactions and categories always stay consistent with each other.

## Depends on
- Step 1: Database setup (`expenses` table with ISO `date` column)
- Step 3: Login + Logout (`session["user_id"]`)
- Step 4: Profile page design (`templates/profile.html`, `static/css/style.css`)
- Step 5: Backend routes for profile page (`get_recent_expenses`, `get_expense_summary`, `get_category_totals`)

## Routes
- `GET /profile` — now accepts optional query parameters `from` and `to` (format `YYYY-MM-DD`, both inclusive) and renders the profile page limited to that range — logged-in only (redirect to `/login` if not authenticated; unchanged)

No other new routes. Filtering uses GET so filtered views are bookmarkable and shareable via URL.

## Database changes
No database changes. The existing `expenses.date` column stores ISO `YYYY-MM-DD` text, which compares correctly as a string in SQL.

The three existing helpers in `database/db.py` gain optional `date_from=None, date_to=None` keyword arguments (existing calls and behaviour unchanged when both are `None`):
- `get_recent_expenses(user_id, limit=10, date_from=None, date_to=None)`
- `get_expense_summary(user_id, date_from=None, date_to=None)`
- `get_category_totals(user_id, date_from=None, date_to=None)`

Add one small private helper in `database/db.py` that builds the optional `AND date >= ? AND date <= ?` clause and its parameter list, so the three queries share it. Only fixed SQL fragments are concatenated; all values go through `?` placeholders.

## Templates
- **Create:** none
- **Modify:** `templates/profile.html`:
  - Add a filter bar above the stat cards: a `<form method="get" action="{{ url_for('profile') }}">` with two `type="date"` inputs (`from`, `to`) pre-filled from the current filter, an "Apply" button, and a "Clear" link to `url_for('profile')`
  - Add preset links (This month, Last 30 days, All time) generated with `url_for('profile', **{'from': ..., 'to': ...})`
  - Context gains `filters` (`date_from`, `date_to` as ISO strings or `""`, and `active` boolean) and `presets` (list of `label`, `date_from`, `date_to`)
  - When a filter is active and nothing matches, show "No expenses in this period" instead of "No expenses yet" in the transactions and category panels
  - Existing context keys (`user`, `stats`, `transactions`, `categories`) and their shapes must not change

## Files to change
- `app.py` — in `profile()`: read and validate `from`/`to`, pass them to the three helpers, build `filters` and `presets` for the template
- `database/db.py` — add the optional date arguments and the shared clause helper
- `templates/profile.html` — filter bar, presets, and the filtered empty-state message
- `static/css/style.css` — styles for the filter bar and preset links using existing CSS variables
- `tests/test_profile.py` — add filter tests

## Files to create
None.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only — never put user-supplied dates into the SQL string
- Passwords hashed with werkzeug (no changes to auth in this step)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- No inline styles
- Every query must still filter by `user_id = ?` using `session["user_id"]`
- Validate `from` and `to` with `datetime.strptime(value, "%Y-%m-%d")`; an empty or malformed value is ignored (treated as no bound) and must never cause a 500
- If both dates are valid and `from` is after `to`, flash an error ("Start date must be on or before end date"), and show the unfiltered data
- Either bound may be given on its own (open-ended range)
- The filter applies to all three sections (stats, transactions, categories) so they stay consistent
- Keep the transaction list limit (10) — filtering narrows which rows are eligible, it does not remove the limit
- Compute preset dates in the view from `date.today()`; do not hardcode dates
- Do not implement add/edit/delete expense routes in this step (Steps 7–9)

## Definition of done
- [ ] `/profile` with no query parameters behaves exactly as in Step 5 (all 8 seeded expenses, total ₹6,640.00)
- [ ] `/profile?from=YYYY-MM-DD&to=YYYY-MM-DD` shows only expenses within that range, inclusive of both endpoints
- [ ] Stats (total, count, top category), the transaction table and the category breakdown all reflect the same filtered set, and category percentages sum against the filtered total
- [ ] Providing only `from` or only `to` filters with an open-ended range
- [ ] The date inputs stay pre-filled with the applied range after submitting
- [ ] "This month", "Last 30 days" and "All time" presets each apply the expected range; "Clear" returns to the unfiltered view
- [ ] A range with no matching expenses returns HTTP 200 with `₹0.00`, `0` transactions, `—` as top category and "No expenses in this period"
- [ ] Malformed dates (e.g. `?from=abc`) return HTTP 200 and are ignored; no error page
- [ ] `from` later than `to` shows a flashed error and the unfiltered data
- [ ] A user never sees another user's expenses under any filter (verified with two accounts)
- [ ] Logged-out access to `/profile?from=...` still redirects to `/login`
- [ ] No hex colour values added to `profile.html` or inline styles
- [ ] `pytest tests/test_profile.py` passes
