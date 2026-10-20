import pytest

from database import db


def register(client, name, email):
    return client.post(
        "/register",
        data={
            "name": name,
            "email": email,
            "password": "password123",
            "confirm_password": "password123",
        },
    )


def test_profile_requires_login(client):
    resp = client.get("/profile")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_demo_user_sees_seeded_data(client, login):
    login()
    html = client.get("/profile").get_data(as_text=True)
    assert "Demo User" in html
    assert "6,640.00" in html
    assert "Shopping" in html
    assert "Groceries" in html


def test_transactions_newest_first(client, login):
    login()
    html = client.get("/profile").get_data(as_text=True)
    assert html.index("Lunch with friends") < html.index("Groceries")


def test_new_user_empty_state(client, login):
    register(client, "Jane Roe", "jane@example.com")
    login("jane@example.com", "password123")
    resp = client.get("/profile")
    html = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert "Jane Roe" in html
    assert "JR" in html
    assert "0.00" in html
    assert "No expenses yet" in html
    assert "Groceries" not in html


def test_users_do_not_see_each_others_expenses(client, login):
    register(client, "Jane Roe", "jane@example.com")
    login("jane@example.com", "password123")
    html = client.get("/profile").get_data(as_text=True)
    assert "Electricity bill" not in html


def test_new_expense_appears_on_reload(client, login):
    login()
    with db.get_db() as conn:
        conn.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description)"
            " VALUES (1, 99, 'Food', '2026-10-25', 'Brand new snack')"
        )
    html = client.get("/profile").get_data(as_text=True)
    assert "Brand new snack" in html


def test_stale_session_redirects_to_login(client, login):
    login()
    with db.get_db() as conn:
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute("DELETE FROM expenses")
        conn.execute("DELETE FROM users")
    resp = client.get("/profile")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


# ------------------------------------------------------------------ #
# Date filter                                                         #
# ------------------------------------------------------------------ #


@pytest.fixture
def dated(client, login):
    """Log in as demo and replace their expenses with known dated rows."""
    login()
    rows = [
        (100, "Food", "2026-01-10", "Jan food"),
        (200, "Transport", "2026-02-15", "Feb ride"),
        (400, "Food", "2026-03-20", "Mar food"),
    ]
    with db.get_db() as conn:
        conn.execute("DELETE FROM expenses WHERE user_id = 1")
        conn.executemany(
            "INSERT INTO expenses (user_id, amount, category, date, description)"
            " VALUES (1, ?, ?, ?, ?)",
            rows,
        )


def test_no_params_is_unfiltered(client, dated):
    html = client.get("/profile").get_data(as_text=True)
    assert "700.00" in html
    assert "Jan food" in html and "Mar food" in html


def test_range_is_inclusive_of_endpoints(client, dated):
    html = client.get("/profile?from=2026-01-10&to=2026-02-15").get_data(as_text=True)
    assert "Jan food" in html and "Feb ride" in html
    assert "Mar food" not in html
    assert "300.00" in html


def test_only_from_or_only_to(client, dated):
    html = client.get("/profile?from=2026-02-01").get_data(as_text=True)
    assert "Feb ride" in html and "Mar food" in html and "Jan food" not in html
    html = client.get("/profile?to=2026-02-01").get_data(as_text=True)
    assert "Jan food" in html and "Feb ride" not in html


def test_stats_and_categories_follow_filter(client, dated):
    html = client.get("/profile?from=2026-02-01&to=2026-03-31").get_data(as_text=True)
    # total 600; Food 400 (67%) is top category, Transport 200 (33%)
    assert "600.00" in html
    assert 'value="67"' in html and 'value="33"' in html
    assert "Jan food" not in html


def test_empty_range_message(client, dated):
    resp = client.get("/profile?from=2025-01-01&to=2025-01-31")
    html = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert "0.00" in html
    assert "—" in html
    assert "No expenses in this period" in html


def test_malformed_dates_are_ignored(client, dated):
    resp = client.get("/profile?from=abc&to=2026-13-40")
    html = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert "700.00" in html


def test_from_after_to_flashes_error_and_shows_all(client, dated):
    html = client.get("/profile?from=2026-03-01&to=2026-01-01").get_data(as_text=True)
    assert "Start date must be on or before end date" in html
    assert "700.00" in html


def test_inputs_are_prefilled(client, dated):
    html = client.get("/profile?from=2026-01-10&to=2026-02-15").get_data(as_text=True)
    assert 'value="2026-01-10"' in html
    assert 'value="2026-02-15"' in html


def test_filter_does_not_leak_other_users(client, login):
    register(client, "Jane Roe", "jane@example.com")
    login("jane@example.com", "password123")
    with db.get_db() as conn:
        jane = conn.execute(
            "SELECT id FROM users WHERE email = 'jane@example.com'"
        ).fetchone()[0]
        conn.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description)"
            " VALUES (?, 50, 'Food', '2026-02-01', 'Jane snack')",
            (jane,),
        )
        conn.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description)"
            " VALUES (1, 999, 'Bills', '2026-02-01', 'Demo secret')"
        )
    html = client.get("/profile?from=2026-01-01&to=2026-12-31").get_data(as_text=True)
    assert "Jane snack" in html
    assert "Demo secret" not in html


def test_filtered_profile_requires_login(client):
    resp = client.get("/profile?from=2026-01-01")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_preset_links_present(client, login):
    login()
    html = client.get("/profile").get_data(as_text=True)
    assert "This month" in html
    assert "Last 30 days" in html
    assert "All time" in html
