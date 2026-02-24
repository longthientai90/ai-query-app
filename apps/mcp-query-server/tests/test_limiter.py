import pytest

from security.limiter import LimitExceededError, enforce_limit


def test_injects_default_limit():
    sql = enforce_limit("SELECT * FROM users", default_limit=100, max_limit=1000)
    assert "LIMIT 100" in sql.upper()


def test_clamps_existing_limit():
    sql = enforce_limit("SELECT * FROM users LIMIT 5000", default_limit=100, max_limit=1000)
    assert "LIMIT 1000" in sql.upper()


def test_respects_max_rows():
    sql = enforce_limit("SELECT * FROM users LIMIT 700", default_limit=100, max_limit=1000, max_rows=50)
    assert "LIMIT 50" in sql.upper()


def test_rejects_invalid_max_rows():
    with pytest.raises(LimitExceededError):
        enforce_limit("SELECT * FROM users", default_limit=100, max_limit=1000, max_rows=0)

