# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Spendly** is a Flask-based expense tracker web application built as a step-by-step learning project. It features user authentication (login/register), expense management (add/edit/delete), and a SQLite database backend. The project is designed with placeholder routes for features to be implemented incrementally.

**Technology Stack:**
- **Backend:** Flask 3.1.3, Python
- **Database:** SQLite with foreign keys enabled
- **Frontend:** HTML templates (Jinja2), CSS, JavaScript
- **Testing:** pytest + pytest-flask

## Setup & Development

### Initial Setup
```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Initialize database (once implemented in database/db.py)
python3 -c "from database.db import init_db, seed_db; init_db(); seed_db()"
```

### Running the Application
```bash
# Start development server (runs on http://localhost:5001)
python3 app.py
```

### Testing
```bash
# Run all tests
pytest

# Run tests with verbose output
pytest -v

# Run a specific test file
pytest tests/test_auth.py

# Run tests matching a pattern
pytest -k "test_login"

# Generate coverage report
pytest --cov
```

## Project Structure

### Core Application Files
- **`app.py`** — Main Flask application entry point. Contains route definitions organized into sections:
  - **Routes:** `/`, `/register`, `/login` (implemented)
  - **Placeholder routes:** `/logout`, `/profile`, `/expenses/*` (to be implemented in Steps 3–9)

### Database Module (`database/`)
- **`db.py`** — Database initialization and connection management (student implementation task). Should contain:
  - `get_db()` — Returns SQLite connection with row_factory and foreign keys enabled
  - `init_db()` — Creates all tables using CREATE TABLE IF NOT EXISTS
  - `seed_db()` — Inserts sample data for development
- **`__init__.py`** — Package init file (empty)

### Frontend (`templates/`, `static/`)
- **`templates/base.html`** — Base template with navbar, main content block, footer, and script injection points
- **`templates/landing.html`, `login.html`, `register.html`** — Page-specific templates extending `base.html`
- **`static/css/style.css`** — Application styling
- **`static/js/main.js`** — Client-side JavaScript

### Configuration
- **`requirements.txt`** — Python dependencies
- **`.gitignore`** — Git exclusions (includes `venv/`, `*.db`, `__pycache__/`, `.env`, `.claude/plans/`)

## Development Notes

### Step-by-Step Nature
This is a learning project organized in implementation steps (mentioned in placeholder route comments):
- **Step 1:** Database setup (`database/db.py`)
- **Step 3:** Logout functionality
- **Step 4:** User profile page
- **Step 7–9:** Expense management (add/edit/delete)

When implementing features, maintain this incremental structure and avoid implementing multiple steps in one PR.

### Database
- SQLite database file is `expense_tracker.db` (in `.gitignore`)
- Always enable foreign keys and row_factory in connections
- Database module is intentionally empty for students to implement

### Flask Routes
Routes use the naming convention `@app.route("/path")` and return rendered templates via `render_template()`. Placeholder routes return plain text strings indicating future implementation.

### URL Generation
Always use `url_for()` helper in templates (already used in `base.html`) to generate dynamic links rather than hardcoding paths.

## Common Tasks

**Add a new route:**
1. Add the `@app.route("/path")` decorator in `app.py`
2. Implement the route function (return `render_template()` or data)
3. If needed, create corresponding template in `templates/`

**Create a new page template:**
1. Create file in `templates/` 
2. Extend `base.html` with `{% extends "base.html" %}`
3. Override `{% block title %}`, `{% block content %}`, etc.

**Run the app and test in browser:**
- Navigate to http://localhost:5001
- Use Flask debug toolbar for debugging (enabled by default with `debug=True`)
