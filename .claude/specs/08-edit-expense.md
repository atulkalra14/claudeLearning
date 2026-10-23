# Spec: Edit Expense

## Overview
This feature lets a signed-in user change an expense they previously recorded. Step 7 added the ability to create expenses; mistakes (wrong amount, category or date) currently cannot be corrected. Each row in the profile page's transactions table gets an "Edit" link that opens `/expenses/<id>/edit`, a form pre-filled with the saved values. Submitting valid data updates the row in place and redirects back to `/profile`, where the stats, transactions and category breakdown reflect the change. A user can only ever edit their own expenses.

## Depends on
- Step 1: Database setup (`expenses` table)
- Step 3: Login + Logout (`session["user_id"]`)
- Step 5/6: Profile page data helpers (`get_recent_expenses`) and the date filter
- Step 7: Add expense (`_parse_expense_form`, `_current_user_id`, `CATEGORIES`, `MAX_AMOUNT`, `MAX_DESCRIPTION_LENGTH`, `templates/add_expense.html`)

## Routes
- `GET /expenses/<int:id>/edit` — render the expense form pre-filled with the saved values — logged-in only (redirect to `/login` if not authenticated); `404` if the expense does not exist or belongs to another user
- `POST /expenses/<int:id>/edit` — validate the form with the same rules as add, update the row, flash a success message and redirect to `/profile`; on validation error re-render the form with the entered values and a flashed error — logged-in only; `404` for a missing or foreign expense

The existing GET-only placeholder `edit_expense(id)` in `app.py` is replaced. The delete placeholder is left untouched (Step 9). Updating data happens only via POST, never via a GET link.

## Database changes
No database changes. The existing `expenses` table already holds every editable field.

Add two helpers to `database/db.py` in the Expenses section:
- `get_expense(user_id, expense_id)` — return the expense row (`id, amount, category, date, description`) only if it belongs to `user_id`, else `None`. The `user_id = ?` condition lives in the SQL so ownership cannot be skipped by a caller.
- `update_expense(user_id, expense_id, amount, category, expense_date, description)` — `UPDATE ... WHERE id = ? AND user_id = ?`; return `True` if a row was updated (`cursor.rowcount == 1`), else `False`.

Change `get_recent_expenses` to also select `id` so the profile page can build edit links. Existing callers and the ordering/limit behaviour are unchanged; adding a column to the SELECT must not break any current test.

## Templates
- **Create:** none. Reuse `templates/add_expense.html` for both add and edit to avoid duplicating the form, driven by context variables: `form_action` (the URL to post to), `page_title`/heading text and `submit_label` ("Add expense" vs "Save changes"). The add route passes the add values; the edit route passes the edit values.
- **Modify:**
  - `templates/add_expense.html` — take the form action, heading, subtitle and submit label from the context instead of hard-coding "Add"; keep all existing fields, escaping and Cancel link
  - `templates/profile.html` — add an "Actions" column to the transactions table with an "Edit" link per row pointing to `url_for('edit_expense', id=tx.id)`

## Files to change
- `app.py` — replace the `edit_expense` placeholder; include `id` in each transaction dict built in `profile()`; pass the new context variables from `add_expense()`
- `database/db.py` — add `get_expense` and `update_expense`; add `id` to `get_recent_expenses`
- `templates/add_expense.html` — parameterise action, heading and submit label
- `templates/profile.html` — Edit column and links
- `static/css/style.css` — small style for the edit link, using existing CSS variables
- `tests/test_profile.py` / `tests/test_07_add_expense.py` — only if the added `id` column or template changes require it

## Files to create
- `tests/test_08_edit_expense.py`

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only — never build SQL from form values or the URL id
- Passwords hashed with werkzeug (no auth changes in this step)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- No inline styles
- Reuse `_parse_expense_form` for validation so add and edit enforce identical rules (amount finite, > 0 and <= `MAX_AMOUNT`; category in `CATEGORIES`; valid ISO date; description trimmed to `MAX_DESCRIPTION_LENGTH`)
- Use `_current_user_id()` for the login and stale-session guard
- Ownership must be enforced in SQL (`WHERE id = ? AND user_id = ?`). A missing expense and another user's expense must be indistinguishable: both return `404`, so ids cannot be probed
- The user id comes from `session["user_id"]`, never from the form or URL
- State changes only on POST; the GET route must never modify data
- On a failed update (`update_expense` returns `False`) return `404`; never a 500
- Re-filled values and flashed messages rely on Jinja autoescaping; no `|safe`
- Use `url_for()` for all links, form actions and redirects
- Do not implement delete (Step 9) and do not change the date-filter behaviour of the profile page

## Definition of done
- [ ] Each transaction row on `/profile` shows an "Edit" link to `/expenses/<id>/edit`
- [ ] Logged out, `GET` and `POST /expenses/<id>/edit` redirect to `/login`, and a POST changes nothing
- [ ] Logged in, `GET /expenses/<id>/edit` for your own expense returns 200 with the amount, category (selected), date and description pre-filled, and the page says "Edit" with a "Save changes" button
- [ ] Submitting valid changes redirects to `/profile`, shows a success message, and the row displays the new values (not a duplicate row)
- [ ] The profile total, transaction count, top category and category breakdown reflect the edited values
- [ ] Changing only one field leaves the others unchanged; clearing the description saves it as empty
- [ ] Missing, zero, negative, non-numeric, `nan`, `inf` or above-the-cap amount shows an error and leaves the saved row unchanged
- [ ] An invalid category or missing/malformed date shows an error and leaves the saved row unchanged
- [ ] After a validation error the entered values stay in the form
- [ ] `GET` and `POST` for an expense id that does not exist return 404
- [ ] `GET` and `POST` for another user's expense return 404 and do not modify it (verified with two accounts)
- [ ] The add-expense flow from Step 7 still works unchanged (same form, "Add expense" button)
- [ ] A description containing `<script>` is displayed escaped on the form and on the profile page
- [ ] No hex colour values added to templates or inline styles
- [ ] `pytest tests/test_08_edit_expense.py` passes, and the full `pytest` run still passes
