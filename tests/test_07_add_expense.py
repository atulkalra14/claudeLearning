from contextlib import closing
from datetime import date

import pytest

from database import db

VALID = {
    "amount": "250.50",
    "category": "Food",
    "date": date.today().isoformat(),
    "description": "Team lunch",
}


def post(client, **overrides):
    return client.post("/expenses/add", data={**VALID, **overrides})


def expense_count():
    with closing(db.get_db()) as conn:
        return conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]


def latest_expense():
    with closing(db.get_db()) as conn:
        return conn.execute(
            "SELECT * FROM expenses ORDER BY id DESC LIMIT 1"
        ).fetchone()


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


def test_get_requires_login(client):
    resp = client.get("/expenses/add")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_post_requires_login_and_inserts_nothing(client):
    before = expense_count()
    resp = post(client)
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]
    assert expense_count() == before


def test_form_renders(client, login):
    login()
    resp = client.get("/expenses/add")
    html = resp.get_data(as_text=True)
    assert resp.status_code == 200
    for cat in db.CATEGORIES:
        assert f'value="{cat}"' in html
    assert f'value="{date.today().isoformat()}"' in html
    # 7 categories plus the disabled placeholder option
    assert html.count("<option value=") == len(db.CATEGORIES) + 1


def test_profile_links_to_add_form_and_cancel_returns(client, login):
    login()
    assert 'href="/expenses/add"' in client.get("/profile").get_data(as_text=True)
    assert 'href="/profile"' in client.get("/expenses/add").get_data(as_text=True)


def test_valid_submission_redirects_and_shows_on_profile(client, login):
    login()
    before = client.get("/profile").get_data(as_text=True)
    assert "6,640.00" in before
    resp = post(client)
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/profile")
    html = client.get("/profile").get_data(as_text=True)
    assert "Expense added" in html
    assert "Team lunch" in html
    assert "6,890.50" in html  # 6,640.00 seeded + 250.50
    assert html.index("Team lunch") < html.index("Lunch with friends")


def test_profile_count_and_category_update_after_add(client, login):
    login()
    post(client, amount="9000", category="Health", description="Surgery")
    html = client.get("/profile").get_data(as_text=True)
    # 8 seeded + 1 new transaction; Health (650 + 9000) becomes the top category
    assert '<span class="stat-value">9</span>' in html
    assert '<span class="stat-value">Health</span>' in html
    assert "9,650.00" in html


def test_whitespace_description_saved_as_null(client, login):
    login()
    post(client, description="   ")
    assert latest_expense()["description"] is None


def test_stale_session_redirects_to_login(client, login):
    login()
    with closing(db.get_db()) as conn:
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute("DELETE FROM expenses")
        conn.execute("DELETE FROM users")
        conn.commit()
    resp = client.get("/expenses/add")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_amount_at_upper_bound_accepted_and_above_rejected(client, login):
    login()
    assert post(client, amount="10000000").status_code == 302
    before = expense_count()
    resp = post(client, amount="10000000.01")
    assert resp.status_code == 200
    assert "auth-error" in resp.get_data(as_text=True)
    assert expense_count() == before


def test_blank_description_is_saved(client, login):
    login()
    before = expense_count()
    resp = post(client, description="")
    assert resp.status_code == 302
    assert expense_count() == before + 1


@pytest.mark.parametrize(
    "overrides",
    [
        {"amount": ""},
        {"amount": "0"},
        {"amount": "-5"},
        {"amount": "abc"},
        {"amount": "nan"},
        {"amount": "inf"},
        {"category": "Nope"},
        {"category": ""},
        {"date": ""},
        {"date": "2025-13-45"},
        {"date": "not-a-date"},
    ],
)
def test_invalid_input_rejected(client, login, overrides):
    login()
    before = expense_count()
    resp = post(client, **overrides)
    assert resp.status_code == 200
    assert "auth-error" in resp.get_data(as_text=True)
    assert expense_count() == before


def test_values_refilled_after_error(client, login):
    login()
    html = post(client, amount="-1").get_data(as_text=True)
    assert 'value="-1"' in html
    assert 'value="Team lunch"' in html
    assert '<option value="Food" selected>' in html


def test_description_is_escaped(client, login):
    login()
    post(client, description="<script>alert(1)</script>")
    html = client.get("/profile").get_data(as_text=True)
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_long_description_truncated(client, login):
    login()
    post(client, description="x" * 201)
    with closing(db.get_db()) as conn:
        row = conn.execute(
            "SELECT description FROM expenses ORDER BY id DESC LIMIT 1"
        ).fetchone()
    assert len(row["description"]) == 200


def test_expense_belongs_to_current_user_only(client, login):
    login()
    post(client, description="Private purchase")
    client.get("/logout")
    register(client, "Jane Roe", "jane@example.com")
    login("jane@example.com", "password123")
    html = client.get("/profile").get_data(as_text=True)
    assert "Private purchase" not in html
