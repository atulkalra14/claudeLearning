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
