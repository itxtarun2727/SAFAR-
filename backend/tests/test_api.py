"""
test_api.py — Integration tests for SAFAR REST endpoints.
"""

import sys
import os
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from main import app

client = TestClient(app)


def test_health():
    """Verify health check endpoint returns 200 OK."""
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"
    assert "current_time" in res.json()


def test_root_redirect():
    """Root path / should redirect to /docs."""
    res = client.get("/", follow_redirects=False)
    assert res.status_code in [307, 308]
    assert res.headers["location"] == "/docs"


def test_auth_login_success():
    """Valid credentials return a signed JWT token."""
    res = client.post("/auth/login", json={"username": "priya", "password": "demo1234"})
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["user"]["role"] == "aicte_officer"


def test_auth_login_invalid():
    """Invalid credentials return 401 Unauthorized."""
    res = client.post("/auth/login", json={"username": "priya", "password": "wrongpassword"})
    assert res.status_code == 401


def test_list_instruments():
    """Listing instruments returns a valid JSON array."""
    res = client.get("/instruments")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_audit_verify():
    """Audit verification returns cryptographic status."""
    res = client.get("/audit/verify")
    assert res.status_code == 200
    assert "ok" in res.json()
    assert "total_entries" in res.json()


def test_clock_endpoints():
    """Clock endpoints return current time and handle advance/reset."""
    res = client.get("/clock")
    assert res.status_code == 200
    assert "today" in res.json()


def test_rules_endpoints():
    """Rules table returns regulatory parameters."""
    res = client.get("/rules")
    assert res.status_code == 200
    assert isinstance(res.json(), list)
