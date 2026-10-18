# Spec: Login and Logout

## Overview
Implement session-based authentication so registered users can sign in and out of Spendly. This step upgrades the existing `GET /login` stub into a working form that accepts a POST, verifies the email and password against the `users` table, and stores the user's id in Flask's `session`. It also replaces the `/logout` placeholder with a route that clears the session. The navbar becomes session-aware so signed-in users see "Sign out" instead of "Sign in" / "Get started". This is the gate for every logged-in feature that follows (profile, expenses).

## Depends on
- Step 01 — Database setup (`users` table, `get_db()`)
- Step 02 — Registration (`create_user()`, `app.secret_key`, flash message pattern)

## Routes
- `GET /login` — render login form; redirect to `/profile` if already signed in — public (already exists as stub, upgrade it)
- `POST /login` — validate credentials, set `session["user_id"]`, redirect to `/profile` — public
- `GET /logout` — clear the session, flash a confirmation, redirect to `/` — logged-in (harmless if not signed in; still redirects to `/`)

## Database changes
No new tables or columns. The existing `users` table already has `email` (UNIQUE) and `password_hash`.

A new DB helper must be added to `database/db.py`:
- `get_user_by_email(email)` — returns the matching `users` row as `sqlite3.Row`, or `None` if no match. Uses a parameterised query.

## Templates
- **Modify**: `templates/login.html`
  - Change the form `action` from the hardcoded `/login` to `url_for('login')`
  - Re-populate the `email` input with the submitted value on a failed attempt (never re-populate the password)
  - Keep the existing flash/error display and all visual design
- **Modify**: `templates/base.html`
  - In the navbar, show "Sign in" and "Get started" only when `session.get("user_id")` is not set
  - When signed in, show a "Sign out" link pointing to `url_for('logout')`
  - Keep all existing visual design

## Files to change
- `app.py` — upgrade `login()` to handle `GET` and `POST`; implement `logout()`; import `session` and the new DB helper; import `check_password_hash`
- `database/db.py` — add `get_user_by_email()` helper
- `templates/login.html` — wire up form action and email re-population
- `templates/base.html` — session-aware navbar links
- `templates/landing.html` — render flashed messages so the logout confirmation is visible

## Files to create
- `templates/profile.html` — minimal placeholder extending `base.html` so the navbar (and "Sign out") is visible after login; real content comes in Step 4

## New dependencies
No new dependencies. Uses `werkzeug.security.check_password_hash` (already installed) and Flask's built-in `session`, `flash`, `redirect` and `url_for`.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only — never use f-strings in SQL
- Passwords hashed with werkzeug — verify with `check_password_hash`, never compare plaintext
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Use `url_for()` for every internal link and form action — never hardcode URLs
- Normalise the submitted email with `.strip().lower()` before lookup, matching how `register()` stores it
- Use one generic error for both an unknown email and a wrong password ("Invalid email or password") so the form does not reveal which emails are registered
- Server-side validation must check that email and password are non-empty before querying
- On failure, re-render the form with a flashed error — do not redirect
- On success, store only `user_id` in `session` (never the hash), flash nothing noisy, and redirect to `url_for('profile')`
- Call `session.clear()` in `logout()`, then flash a "signed out" message and redirect to `url_for('landing')`
- Use `abort(405)` if an unsupported HTTP method reaches `login()`
- Do not implement the profile page, route protection decorators or expense features — those belong to later steps

## Definition of done
- [ ] `GET /login` renders the sign-in form without errors
- [ ] Signing in as the seeded demo user (`demo@spendly.com` / `demo123`) redirects to `/profile`
- [ ] A user created through `/register` can sign in with the credentials they registered with
- [ ] Signing in with a wrong password re-renders the form with "Invalid email or password" and no session is set
- [ ] Signing in with an unregistered email shows the same "Invalid email or password" message
- [ ] Submitting with an empty email or password re-renders the form with a validation error
- [ ] Email matching is case-insensitive (`DEMO@Spendly.com` signs in successfully)
- [ ] After a failed attempt the email field keeps its value and the password field is empty
- [ ] While signed in, the navbar shows "Sign out" and hides "Sign in" / "Get started"
- [ ] While signed out, the navbar shows "Sign in" and "Get started" and hides "Sign out"
- [ ] Visiting `/login` while already signed in redirects to `/profile`
- [ ] Clicking "Sign out" clears the session, lands on `/`, and the navbar reverts to the signed-out links
- [ ] The session cookie contains no password or hash (only the user id)
