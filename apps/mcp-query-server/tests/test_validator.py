import pytest

from security.validator import SQLValidationError, validate_sql


def test_accepts_select():
    validate_sql("SELECT id FROM users")


def test_accepts_with_select():
    validate_sql("WITH x AS (SELECT 1 AS n) SELECT n FROM x")


@pytest.mark.parametrize(
    "sql",
    [
        "INSERT INTO users(id) VALUES (1)",
        "UPDATE users SET id = 2",
        "DELETE FROM users",
        "DROP TABLE users",
    ],
)
def test_rejects_mutation(sql):
    with pytest.raises(SQLValidationError):
        validate_sql(sql)


def test_rejects_comments():
    with pytest.raises(SQLValidationError):
        validate_sql("SELECT 1 -- comment")


def test_rejects_risky_function():
    with pytest.raises(SQLValidationError):
        validate_sql("SELECT pg_read_file('/etc/passwd')")


def test_rejects_multistatement():
    with pytest.raises(SQLValidationError):
        validate_sql("SELECT 1; SELECT 2")

