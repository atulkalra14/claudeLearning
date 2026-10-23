"""Tests for spec 06: date-range filter on /profile.

Rows use fixed, explicit dates inserted through database.db.get_db().
"""

import re
from contextlib import closing
from datetime import date
from pathlib import Path

import pytest

from database import db

DEMO_ID = 1

# (amount, category, date, description) for the demo user
DEMO_ROWS = [
    (100.00, "Food", "2026-01-01", "RowJanFirst"),
    (200.00, "Transport", "2026-01-15", "RowJanMid"),
    (300.00, "Bills", "2026-02-01", "RowFebFirst"),
    (400.00, "Food", "2026-02-15", "RowFebMid"),
    (500.00, "Health", "2026-03-01", "RowMarFirst"),
]
OTHER_ROW = (9999.00, "Shopping", "2026-02-10", "OtherUserSecret")

ALL_DESCS = [r[3] for r in DEMO_ROWS]


def _insert(user_id, rows):
    with closing(db.get_db()) as conn:
        conn.executemany(
            "INSERT INTO expenses (user_id, amount, category, date, description)"
            " VALUES (?, ?, ?, ?, ?)",
            [(user_id, a, c, d, desc) for a, c, d, desc in rows],
        )
        conn.commit()


@pytest.fixture
def known(app):
    """Demo user with only the fixed rows above, plus another user's row."""
    with closing(db.get_db()) as conn:
        conn.execute("DELETE FROM expenses WHERE user_id = ?", (DEMO_ID,))
        conn.commit()
    _insert(DEMO_ID, DEMO_ROWS)
    other_id = db.create_user("Other", "other@spendly.com", "other123")
    _insert(other_id, [OTHER_ROW])
    return other_id


@pytest.fixture
def demo(known, client, login):
    login()
    return client


def _get(client, query=""):
    return client.get("/profile" + query)


def _present(resp, descs):
    return [d for d in ALL_DESCS if d.encode() in resp.data] == list(descs) or set(
        d for d in ALL_DESCS if d.encode() in resp.data
    ) == set(descs)


def _form_html(html):
    m = re.search(r"<form[^>]*method=\"get\"[^>]*>.*?</form>", html, re.S | re.I)
    assert m, "Expected a GET filter form on the profile page"
    return m.group(0)


class TestNoParams:
    def test_no_params_shows_all_rows_unfiltered(self, demo):
        resp = _get(demo)
        assert resp.status_code == 200
        assert _present(resp, ALL_DESCS), "All rows expected without a filter"
        assert "₹1,500.00".encode() in resp.data

    def test_empty_params_equal_no_params(self, demo):
        resp = _get(demo, "?from=&to=")
        assert resp.status_code == 200
        assert _present(resp, ALL_DESCS)
        assert "₹1,500.00".encode() in resp.data

    def test_seeded_demo_unfiltered_total(self, app, client, login):
        login()
        resp = _get(client)
        assert resp.status_code == 200
        assert "₹6,640.00".encode() in resp.data


class TestRangeFilter:
    def test_from_and_to_inclusive_endpoints(self, demo):
        resp = _get(demo, "?from=2026-01-15&to=2026-02-15")
        assert resp.status_code == 200
        assert _present(resp, ["RowJanMid", "RowFebFirst", "RowFebMid"])
        assert "₹900.00".encode() in resp.data

    def test_single_day_range_is_inclusive(self, demo):
        resp = _get(demo, "?from=2026-02-01&to=2026-02-01")
        assert _present(resp, ["RowFebFirst"])
        assert "₹300.00".encode() in resp.data

    def test_only_from_is_open_ended(self, demo):
        resp = _get(demo, "?from=2026-02-01")
        assert resp.status_code == 200
        assert _present(resp, ["RowFebFirst", "RowFebMid", "RowMarFirst"])
        assert "₹1,200.00".encode() in resp.data

    def test_only_to_is_open_ended(self, demo):
        resp = _get(demo, "?to=2026-01-15")
        assert resp.status_code == 200
        assert _present(resp, ["RowJanFirst", "RowJanMid"])
        assert "₹300.00".encode() in resp.data

    def test_stats_transactions_categories_consistent(self, demo):
        # Feb only: Bills 300 + Food 400 = 700, top category Food.
        resp = _get(demo, "?from=2026-02-01&to=2026-02-28")
        html = resp.data.decode()
        assert _present(resp, ["RowFebFirst", "RowFebMid"])
        assert "₹700.00" in html
        assert "Food" in html and "Bills" in html
        # Categories outside the range must not appear anywhere.
        assert "Transport" not in html
        assert "Health" not in html
        # Percentages are against the filtered total (400/700 ~ 57, 300/700 ~ 43)
        assert re.search(r"\b57\s*%", html), "Food should be ~57% of filtered total"
        assert re.search(r"\b43\s*%", html), "Bills should be ~43% of filtered total"

    def test_top_category_reflects_filter(self, demo):
        # Jan only: Transport 200 beats Food 100.
        html = _get(demo, "?from=2026-01-01&to=2026-01-31").data.decode()
        assert "Transport" in html
        assert "Health" not in html


class TestEmptyRange:
    def test_empty_range_shows_zero_state(self, demo):
        resp = _get(demo, "?from=2025-01-01&to=2025-01-31")
        html = resp.data.decode()
        assert resp.status_code == 200
        assert "No expenses in this period" in html
        assert "No expenses yet" not in html
        assert "₹0.00" in html
        assert "—" in html
        assert not any(d in html for d in ALL_DESCS)

    def test_no_filter_and_no_expenses_says_no_expenses_yet(self, app, client):
        db.create_user("Fresh", "fresh@spendly.com", "fresh123")
        client.post(
            "/login", data={"email": "fresh@spendly.com", "password": "fresh123"}
        )
        html = _get(client).data.decode()
        assert "No expenses yet" in html
        assert "No expenses in this period" not in html


class TestInvalidInput:
    @pytest.mark.parametrize(
        "query",
        [
            "?from=abc",
            "?to=abc",
            "?from=abc&to=xyz",
            "?from=2026-13-45",
            "?to=2026-02-30",
            "?from=01/02/2026",
            "?from=%20&to=%20",
        ],
    )
    def test_malformed_dates_ignored_with_200(self, demo, query):
        resp = _get(demo, query)
        assert resp.status_code == 200, f"{query} must not error"
        assert _present(resp, ALL_DESCS)

    def test_malformed_from_with_valid_to_uses_only_to(self, demo):
        resp = _get(demo, "?from=abc&to=2026-01-15")
        assert resp.status_code == 200
        assert _present(resp, ["RowJanFirst", "RowJanMid"])

    def test_from_after_to_flashes_error_and_shows_unfiltered(self, demo):
        resp = _get(demo, "?from=2026-03-01&to=2026-01-01")
        assert resp.status_code == 200
        assert b"Start date must be on or before end date" in resp.data
        assert _present(resp, ALL_DESCS)
        assert "₹1,500.00".encode() in resp.data

    def test_equal_from_and_to_is_not_an_error(self, demo):
        resp = _get(demo, "?from=2026-01-15&to=2026-01-15")
        assert b"Start date must be on or before end date" not in resp.data

    @pytest.mark.parametrize(
        "query",
        [
            "?from=2026-01-01'%20OR%20'1'='1",
            "?to=2026-01-01'%20OR%20'1'='1",
            "?from=1;DROP%20TABLE%20expenses;--",
            "?from='%20OR%201=1--&to='%20OR%201=1--",
        ],
    )
    def test_sql_injection_values_safe(self, demo, query):
        resp = _get(demo, query)
        assert resp.status_code == 200
        assert b"OtherUserSecret" not in resp.data
        # Table still intact and data still shown.
        again = _get(demo)
        assert _present(again, ALL_DESCS)


class TestFormAndPresets:
    def test_inputs_prefilled_with_applied_range(self, demo):
        html = _get(demo, "?from=2026-02-01&to=2026-02-28").data.decode()
        form = _form_html(html)
        assert 'name="from"' in form and 'name="to"' in form
        assert form.count('type="date"') == 2
        assert 'value="2026-02-01"' in form
        assert 'value="2026-02-28"' in form
        assert "Apply" in form

    def test_inputs_empty_without_filter(self, demo):
        form = _form_html(_get(demo).data.decode())
        assert 'value="2026' not in form

    def test_form_posts_to_profile_via_get(self, demo):
        form = _form_html(_get(demo).data.decode())
        assert re.search(r'action="/profile"', form)

    def test_clear_link_returns_to_unfiltered(self, demo):
        html = _get(demo, "?from=2026-02-01&to=2026-02-28").data.decode()
        assert "Clear" in html
        assert re.search(r'<a[^>]+href="/profile"[^>]*>\s*Clear', html)
        assert _present(demo.get("/profile"), ALL_DESCS)

    def test_preset_links_present(self, demo):
        html = _get(demo).data.decode()
        for label in ("This month", "Last 30 days", "All time"):
            assert label in html, f"Missing preset {label}"

    def test_this_month_preset_uses_current_month_start(self, demo):
        html = _get(demo).data.decode()
        today = date.today()
        assert f"from={today.replace(day=1).isoformat()}" in html

    def test_last_30_days_preset_ends_today(self, demo):
        html = _get(demo).data.decode()
        assert f"to={date.today().isoformat()}" in html

    def test_all_time_preset_is_unfiltered_link(self, demo):
        html = _get(demo).data.decode()
        m = re.search(r'<a[^>]+href="([^"]*)"[^>]*>\s*All time', html)
        assert m, "All time link expected"
        resp = demo.get(m.group(1).replace("&amp;", "&"))
        assert resp.status_code == 200
        assert _present(resp, ALL_DESCS)

    def test_this_month_preset_link_works(self, demo):
        html = _get(demo).data.decode()
        m = re.search(r'<a[^>]+href="([^"]*)"[^>]*>\s*This month', html)
        assert m, "This month link expected"
        resp = demo.get(m.group(1).replace("&amp;", "&"))
        assert resp.status_code == 200

    def test_filter_markup_has_no_inline_style(self, demo):
        form = _form_html(_get(demo, "?from=2026-02-01").data.decode())
        assert "style=" not in form

    def test_profile_template_has_no_inline_style_or_hex(self):
        src = (
            Path(__file__).resolve().parent.parent / "templates" / "profile.html"
        ).read_text(encoding="utf-8")
        assert "style=" not in src, "No inline styles allowed"
        assert not re.search(
            r"[:\s\"'(]#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b", src
        ), "No hex colour values allowed"

    def test_rendered_form_has_no_hex_colours(self, demo):
        form = _form_html(_get(demo).data.decode())
        assert not re.search(r"#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b", form)


class TestAuthAndIsolation:
    def test_logged_out_filtered_profile_redirects_to_login(self, client):
        resp = client.get("/profile?from=2026-01-01&to=2026-12-31")
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]

    def test_other_users_rows_never_shown_under_filter(self, demo):
        resp = _get(demo, "?from=2026-02-10&to=2026-02-10")
        assert b"OtherUserSecret" not in resp.data
        assert "9,999".encode() not in resp.data
        assert "No expenses in this period" in resp.data.decode()

    def test_other_user_sees_only_own_rows(self, known, app):
        c = app.test_client()
        c.post("/login", data={"email": "other@spendly.com", "password": "other123"})
        resp = _get(c, "?from=2026-01-01&to=2026-12-31")
        assert b"OtherUserSecret" in resp.data
        assert not any(d.encode() in resp.data for d in ALL_DESCS)
        assert "₹9,999.00".encode() in resp.data


class TestTransactionLimit:
    def test_limit_of_10_applies_under_filter(self, known, client, login):
        _insert(
            DEMO_ID,
            [
                (10.0, "Other", f"2026-04-{i:02d}", f"Bulk{i:02d}x")
                for i in range(1, 13)
            ],
        )
        login()
        resp = _get(client, "?from=2026-04-01&to=2026-04-30")
        assert resp.status_code == 200
        for i in range(3, 13):
            assert f"Bulk{i:02d}x".encode() in resp.data
        for i in (1, 2):
            assert f"Bulk{i:02d}x".encode() not in resp.data
        assert "₹120.00".encode() in resp.data  # stats cover all 12 rows

    def test_helper_limit_applies_under_filter(self, known):
        _insert(
            DEMO_ID,
            [(10.0, "Other", f"2026-04-{i:02d}", f"B{i}") for i in range(1, 13)],
        )
        rows = db.get_recent_expenses(
            DEMO_ID, date_from="2026-04-01", date_to="2026-04-30"
        )
        assert len(rows) == 10


class TestDbHelpers:
    def test_recent_expenses_unchanged_when_none(self, known):
        rows = db.get_recent_expenses(DEMO_ID, date_from=None, date_to=None)
        assert [r["description"] for r in rows] == list(reversed(ALL_DESCS))
        assert [r["description"] for r in rows] == [
            r["description"] for r in db.get_recent_expenses(DEMO_ID)
        ]

    def test_recent_expenses_inclusive_range_newest_first(self, known):
        rows = db.get_recent_expenses(
            DEMO_ID, date_from="2026-01-15", date_to="2026-02-15"
        )
        assert [r["description"] for r in rows] == [
            "RowFebMid",
            "RowFebFirst",
            "RowJanMid",
        ]

    def test_recent_expenses_open_ended(self, known):
        only_from = db.get_recent_expenses(DEMO_ID, date_from="2026-03-01")
        only_to = db.get_recent_expenses(DEMO_ID, date_to="2026-01-01")
        assert [r["description"] for r in only_from] == ["RowMarFirst"]
        assert [r["description"] for r in only_to] == ["RowJanFirst"]

    def test_recent_expenses_scoped_to_user(self, known):
        rows = db.get_recent_expenses(
            known, date_from="2026-01-01", date_to="2026-12-31"
        )
        assert [r["description"] for r in rows] == ["OtherUserSecret"]

    def test_summary_unchanged_when_none(self, known):
        total, count, top = db.get_expense_summary(
            DEMO_ID, date_from=None, date_to=None
        )
        assert (total, count) == (1500.0, 5)
        assert top in ("Food", "Health")  # tied at 500 each
        assert db.get_expense_summary(DEMO_ID) == (total, count, top)

    def test_summary_with_range(self, known):
        total, count, top = db.get_expense_summary(
            DEMO_ID, date_from="2026-01-01", date_to="2026-01-31"
        )
        assert (total, count, top) == (300.0, 2, "Transport")

    def test_summary_empty_range(self, known):
        total, count, top = db.get_expense_summary(
            DEMO_ID, date_from="2025-01-01", date_to="2025-01-31"
        )
        assert total == 0 and count == 0 and top is None

    def test_category_totals_unchanged_when_none(self, known):
        rows = db.get_category_totals(DEMO_ID, date_from=None, date_to=None)
        assert {r["category"]: r["total"] for r in rows} == {
            "Food": 500.0,
            "Transport": 200.0,
            "Bills": 300.0,
            "Health": 500.0,
        }

    def test_category_totals_with_range(self, known):
        rows = db.get_category_totals(
            DEMO_ID, date_from="2026-02-01", date_to="2026-02-28"
        )
        assert [(r["category"], r["total"]) for r in rows] == [
            ("Food", 400.0),
            ("Bills", 300.0),
        ]

    def test_category_totals_scoped_to_user(self, known):
        rows = db.get_category_totals(
            known, date_from="2026-02-01", date_to="2026-02-28"
        )
        assert [(r["category"], r["total"]) for r in rows] == [("Shopping", 9999.0)]

    @pytest.mark.parametrize(
        "bad", ["2026-01-01' OR '1'='1", "'; DROP TABLE expenses;--"]
    )
    def test_helpers_treat_values_as_data(self, known, bad):
        assert db.get_recent_expenses(DEMO_ID, date_from=bad) is not None
        db.get_expense_summary(DEMO_ID, date_to=bad)
        db.get_category_totals(DEMO_ID, date_from=bad, date_to=bad)
        # Table intact and no other-user leakage.
        rows = db.get_recent_expenses(DEMO_ID, date_to=bad)
        assert all(r["description"] != "OtherUserSecret" for r in rows)
        assert len(db.get_recent_expenses(DEMO_ID)) == 5
