import pytest

import app as app_module
from database import db


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DATABASE", str(tmp_path / "test.db"))
    db.init_db()
    db.seed_db()
    app_module.app.config.update(TESTING=True)
    return app_module.app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def login(client):
    def _login(email="demo@spendly.com", password="demo123"):
        return client.post("/login", data={"email": email, "password": password})
    return _login
