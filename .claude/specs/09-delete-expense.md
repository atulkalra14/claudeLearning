# Spec: Delete Expense

## Overview
This feature lets a signed-in user permanently remove an expense they previously recorded. Steps 7 and 8 added creating and editing expenses; wrong or duplicate entries still cannot be removed. Each row in the profile page's transactions table gets a "Delete" button next to "Edit". Clicking it asks the user to confirm, then submits a POST to `/expenses/<id>/delete`, which deletes the row and redirects back to `/profile`, where the stats, transactions and category breakdown no longer include it. A user can only ever delete their own expenses.

## Depends on
- Step 1: Database setup (`expenses` table)
- Step 3: Login + Logout (`session["user_id"]`)
- Step 5/6: Profile page data helpers and the date filter
- Step 7: Add expense (`_current_user_id`)
- Step 8: Edit expense (`get_expense`, the Actions column and `.edit` link styling in `templates/profile.html`, `id` in each transaction dict)

## Routes
- `POST /expenses/<int:id>/delete` — delete the expense, flash "Expense deleted" and redirect to `/profile` — logged-in only (redirect to `/login` if not authenticated); `404` if the expense does not exist or belongs to another user

The existing GET placeholder `delete_expense(id)` in `app.py` is replaced and becomes POST-only. A `GET` to the URL returns `405` and never modifies data (deleting via a link would let prefetchers, crawlers or a malicious `<img>` delete data).

## Database changes
No schema changes.

Add one helper to `database/db.py` in the Expenses section:
- `delete_expense(user_id, expense_id)` — `DELETE FROM expenses WHERE id = ? AND user_id = ?`; commit; return `True` if a row was deleted (`cursor.rowcount == 1`), else `False`. The `user_id = ?` condition lives in the SQL so ownership cannot be skipped by a caller.

## Templates
- **Create:** none
- **Modify:**
  - `templates/profile.html` — in the Actions column add, beside the Edit link, a small `<form method="post" action="{{ url_for('delete_expense', id=tx.id) }}">` containing a "Delete" submit button; the form carries a `data-confirm` attribute with the confirmation message (e.g. "Delete this expense? This cannot be undone.")

## Files to change
- `app.py` — import `delete_expense`; replace the `delete_expense` route placeholder with a POST-only route
- `database/db.py` — add `delete_expense`
- `templates/profile.html` — Delete form/button per transaction row
- `static/js/main.js` — one delegated `submit` listener: if the form has `data-confirm` and `window.confirm()` returns false, call `preventDefault()`
- `static/css/style.css` — style the Delete button (danger styling using existing CSS variables; button must look consistent with the Edit link and sit inline with it)

## Files to create
- `tests/test_09_delete_expense.py`

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only — never build SQL from the URL id
- Passwords hashed with werkzeug (no auth changes in this step)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- No inline styles and no inline JS handlers (`onclick`/`onsubmit`); confirmation lives in `static/js/main.js`
- Route is `methods=["POST"]` only; the function name stays `delete_expense` so `url_for('delete_expense', id=...)` works. Name the db helper import so it does not shadow the route function (e.g. `from database import db` style alias, or import `delete_expense as delete_expense_row`)
- Use `_current_user_id()` for the login and stale-session guard
- Ownership must be enforced in SQL (`WHERE id = ? AND user_id = ?`). A missing expense and another user's expense must be indistinguishable: both return `404`, so ids cannot be probed
- The user id comes from `session["user_id"]`, never from the form or URL
- When `delete_expense` returns `False` respond `404`; never a 500
- Use `url_for()` for all links, form actions and redirects
- Deleting must keep the user on the profile page; do not change the date-filter behaviour (it is acceptable that the redirect drops any active filter)
- Do not change add or edit behaviour

## Definition of done
- [ ] Each transaction row on `/profile` shows a "Delete" button next to "Edit"
- [ ] Clicking Delete shows a browser confirmation; cancelling leaves the expense in place and does not submit
- [ ] Confirming redirects to `/profile`, shows an "Expense deleted" message, and the row is gone
- [ ] The profile total, transaction count, top category and category breakdown no longer include the deleted expense
- [ ] Deleting the user's last expense shows the profile's empty state without errors
- [ ] Only the chosen expense is removed; other expenses (including the user's others) are unchanged
- [ ] Logged out, `POST /expenses/<id>/delete` redirects to `/login` and deletes nothing
- [ ] `GET /expenses/<id>/delete` returns 405 and deletes nothing
- [ ] `POST` for an expense id that does not exist returns 404
- [ ] `POST` for another user's expense returns 404 and the expense still exists (verified with two accounts)
- [ ] Deleting the same expense twice: the second request returns 404, not a 500
- [ ] Add (Step 7) and Edit (Step 8) flows still work unchanged
- [ ] No hex colour values added to templates, CSS rules or inline styles
- [ ] `pytest tests/test_09_delete_expense.py` passes, and the full `pytest` run still passes
