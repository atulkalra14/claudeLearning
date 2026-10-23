from contextlib import closing

from database import db

DEMO_EMAIL = "demo@spendly.com"


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


def get_row(expense_id):
    with closing(db.get_db()) as conn:
        return conn.execute(
            "SELECT * FROM expenses WHERE id = ?", (expense_id,)
        ).fetchone()


def expense_count():
    with closing(db.get_db()) as conn:
        return conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]


def demo_expense(description="Groceries"):
    with closing(db.get_db()) as conn:
        return conn.execute(
            "SELECT * FROM expenses WHERE description = ?", (description,)
        ).fetchone()


def delete_url(expense_id):
    return f"/expenses/{expense_id}/delete"


# ------------------------------------------------------------------ #
# Entry point on the profile page                                     #
# ------------------------------------------------------------------ #


def test_profile_shows_delete_form_for_each_row(client, login):
    login()
    html = client.get("/profile").get_data(as_text=True)
    row = demo_expense()
    assert f'action="{delete_url(row["id"])}"' in html
    assert html.count('class="tx-delete"') == 8
    assert "data-confirm=" in html


# ------------------------------------------------------------------ #
# Auth and method guards                                              #
# ------------------------------------------------------------------ #


def test_post_requires_login_and_deletes_nothing(client):
    row = demo_expense()
    resp = client.post(delete_url(row["id"]))
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]
    assert get_row(row["id"]) is not None


def test_get_is_not_allowed_and_deletes_nothing(client, login):
    login()
    row = demo_expense()
    assert client.get(delete_url(row["id"])).status_code == 405
    assert get_row(row["id"]) is not None


# ------------------------------------------------------------------ #
# Successful delete                                                   #
# ------------------------------------------------------------------ #


def test_delete_removes_only_that_expense(client, login):
    login()
    row = demo_expense()
    before = expense_count()
    resp = client.post(delete_url(row["id"]))
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/profile")
    assert get_row(row["id"]) is None
    assert expense_count() == before - 1


def test_delete_flashes_message_and_updates_profile(client, login):
    login()
    row = demo_expense()
    resp = client.post(delete_url(row["id"]), follow_redirects=True)
    html = resp.get_data(as_text=True)
    assert "Expense deleted" in html
    assert "Groceries" not in html
    assert html.count('class="tx-delete"') == 7


def test_deleting_last_expense_shows_empty_state(client, login):
    login()
    with closing(db.get_db()) as conn:
        ids = [r["id"] for r in conn.execute("SELECT id FROM expenses")]
    for expense_id in ids:
        client.post(delete_url(expense_id))
    resp = client.get("/profile")
    assert resp.status_code == 200
    assert 'class="tx-delete"' not in resp.get_data(as_text=True)


# ------------------------------------------------------------------ #
# Missing and foreign expenses                                        #
# ------------------------------------------------------------------ #


def test_missing_expense_returns_404(client, login):
    login()
    assert client.post(delete_url(99999)).status_code == 404


def test_other_users_expense_returns_404_and_is_kept(client, login):
    row = demo_expense()
    register(client, "Other", "other@example.com")
    login("other@example.com", "password123")
    assert client.post(delete_url(row["id"])).status_code == 404
    assert get_row(row["id"]) is not None


def test_second_delete_returns_404(client, login):
    login()
    row = demo_expense()
    assert client.post(delete_url(row["id"])).status_code == 302
    assert client.post(delete_url(row["id"])).status_code == 404
