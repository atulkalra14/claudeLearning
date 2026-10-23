from contextlib import closing
from datetime import date

import pytest

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
    """Return the seeded demo expense row with this description."""
    with closing(db.get_db()) as conn:
        return conn.execute(
            "SELECT * FROM expenses WHERE description = ?", (description,)
        ).fetchone()


def valid_data(row, **overrides):
    data = {
        "amount": f"{row['amount']:.2f}",
        "category": row["category"],
        "date": row["date"],
        "description": row["description"] or "",
    }
    data.update(overrides)
    return data


def edit_url(expense_id):
    return f"/expenses/{expense_id}/edit"


# ------------------------------------------------------------------ #
# Entry point on the profile page                                     #
# ------------------------------------------------------------------ #


def test_profile_shows_edit_link_for_each_row(client, login):
    login()
    html = client.get("/profile").get_data(as_text=True)
    row = demo_expense()
    assert f'href="{edit_url(row["id"])}"' in html
    assert html.count('class="tx-edit"') == 8


# ------------------------------------------------------------------ #
# Auth guard                                                          #
# ------------------------------------------------------------------ #


def test_get_requires_login(client):
    row = demo_expense()
    resp = client.get(edit_url(row["id"]))
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_post_requires_login_and_changes_nothing(client):
    row = demo_expense()
    resp = client.post(edit_url(row["id"]), data=valid_data(row, amount="1.00"))
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]
    assert get_row(row["id"])["amount"] == row["amount"]


# ------------------------------------------------------------------ #
# GET form                                                            #
# ------------------------------------------------------------------ #


def test_form_is_prefilled(client, login):
    login()
    row = demo_expense()
    resp = client.get(edit_url(row["id"]))
    html = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert "Edit expense" in html
    assert "Save changes" in html
    assert 'value="450.00"' in html
    assert f'value="{row["date"]}"' in html
    assert 'value="Groceries"' in html
    assert '<option value="Food" selected>' in html
    assert f'action="{edit_url(row["id"])}"' in html


# ------------------------------------------------------------------ #
# Valid updates                                                       #
# ------------------------------------------------------------------ #


def test_valid_update_saves_and_redirects(client, login):
    login()
    row = demo_expense()
    before = expense_count()
    resp = client.post(
        edit_url(row["id"]),
        data=valid_data(
            row,
            amount="500.25",
            category="Shopping",
            date=date.today().isoformat(),
            description="Updated groceries",
        ),
    )
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/profile")

    updated = get_row(row["id"])
    assert updated["amount"] == 500.25
    assert updated["category"] == "Shopping"
    assert updated["date"] == date.today().isoformat()
    assert updated["description"] == "Updated groceries"
    assert expense_count() == before  # edited in place, not duplicated


def test_profile_reflects_edit(client, login):
    login()
    row = demo_expense()
    client.post(edit_url(row["id"]), data=valid_data(row, amount="1450.00"))
    html = client.get("/profile").get_data(as_text=True)
    assert "Expense updated" in html
    assert "7,640.00" in html  # 6,640 seeded - 450 + 1,450
    assert "1,450.00" in html


def test_changing_one_field_keeps_the_rest(client, login):
    login()
    row = demo_expense()
    client.post(edit_url(row["id"]), data=valid_data(row, amount="460.00"))
    updated = get_row(row["id"])
    assert updated["amount"] == 460.00
    assert updated["category"] == row["category"]
    assert updated["date"] == row["date"]
    assert updated["description"] == row["description"]


def test_clearing_description_is_saved(client, login):
    login()
    row = demo_expense()
    client.post(edit_url(row["id"]), data=valid_data(row, description=""))
    assert not get_row(row["id"])["description"]


# ------------------------------------------------------------------ #
# Validation errors                                                   #
# ------------------------------------------------------------------ #


@pytest.mark.parametrize(
    "overrides",
    [
        {"amount": ""},
        {"amount": "0"},
        {"amount": "-5"},
        {"amount": "abc"},
        {"amount": "nan"},
        {"amount": "inf"},
        {"amount": "10000000.01"},
        {"category": "Nope"},
        {"category": ""},
        {"date": ""},
        {"date": "2025-13-45"},
        {"date": "not-a-date"},
    ],
)
def test_invalid_input_rejected_and_row_unchanged(client, login, overrides):
    login()
    row = demo_expense()
    resp = client.post(edit_url(row["id"]), data=valid_data(row, **overrides))
    assert resp.status_code == 200
    assert "auth-error" in resp.get_data(as_text=True)
    unchanged = get_row(row["id"])
    assert dict(unchanged) == dict(row)


def test_values_refilled_after_error(client, login):
    login()
    row = demo_expense()
    html = client.post(
        edit_url(row["id"]),
        data=valid_data(row, amount="-1", description="Keep me"),
    ).get_data(as_text=True)
    assert 'value="-1"' in html
    assert 'value="Keep me"' in html
    assert "Save changes" in html


# ------------------------------------------------------------------ #
# Missing and foreign expenses                                        #
# ------------------------------------------------------------------ #


def test_nonexistent_expense_returns_404(client, login):
    login()
    assert client.get(edit_url(99999)).status_code == 404
    resp = client.post(
        edit_url(99999),
        data={
            "amount": "1",
            "category": "Food",
            "date": "2026-01-01",
            "description": "",
        },
    )
    assert resp.status_code == 404


def test_other_users_expense_returns_404_and_is_untouched(client, login):
    row = demo_expense()
    client.get("/logout")
    register(client, "Jane Roe", "jane@example.com")
    login("jane@example.com", "password123")

    assert client.get(edit_url(row["id"])).status_code == 404
    resp = client.post(edit_url(row["id"]), data=valid_data(row, amount="1.00"))
    assert resp.status_code == 404
    assert dict(get_row(row["id"])) == dict(row)


# ------------------------------------------------------------------ #
# Escaping and regressions                                            #
# ------------------------------------------------------------------ #


def test_description_is_escaped_on_form_and_profile(client, login):
    login()
    row = demo_expense()
    client.post(
        edit_url(row["id"]),
        data=valid_data(row, description="<script>alert(1)</script>"),
    )
    for url in ("/profile", edit_url(row["id"])):
        html = client.get(url).get_data(as_text=True)
        assert "<script>alert(1)</script>" not in html
        assert "&lt;script&gt;" in html


def test_add_form_is_unchanged(client, login):
    login()
    html = client.get("/expenses/add").get_data(as_text=True)
    assert "Add an expense" in html
    assert ">Add expense</button>" in html
    assert 'action="/expenses/add"' in html
