import pytest

from app.auth.validation import validate_email

INVALID_MESSAGE = "Enter a valid email address"


@pytest.mark.parametrize(
    ("raw", "normalized"),
    [
        ("student@university.edu", "student@university.edu"),
        ("  Student@University.EDU ", "student@university.edu"),
        ("first.last+clinic@uni.edu", "first.last+clinic@uni.edu"),
        ("a_b-c%d@health.sub-school.edu", "a_b-c%d@health.sub-school.edu"),
    ],
)
def test_accepts_and_normalizes_valid_emails(raw, normalized):
    assert validate_email(raw) == normalized


@pytest.mark.parametrize("email", ["", "   "])
def test_requires_email(email):
    with pytest.raises(ValueError, match="Email is required."):
        validate_email(email)


@pytest.mark.parametrize(
    "email",
    [
        "student",
        "student@",
        "@university.edu",
        "student@university",
        "student@university.e",
        "student@-university.edu",
        "student@university-.edu",
        "stu dent@university.edu",
        "stüdent@university.edu",
        "student@@university.edu",
        "first..last@university.edu",
    ],
)
def test_rejects_malformed_emails(email):
    with pytest.raises(ValueError, match=INVALID_MESSAGE):
        validate_email(email)


# Classic payloads an attacker would type into a username box.
SQL_INJECTION_PAYLOADS = [
    "' OR '1'='1",
    "' OR 1=1 --",
    '" OR ""="',
    "admin'--",
    "admin@university.edu'--",
    "admin@university.edu--",
    "admin--@university.edu",
    "admin@university.edu; DROP TABLE users;",
    "x@y.edu' UNION SELECT password FROM users --",
    "x@y.edu/*comment*/",
    "x@y.edu\x00",
    "1;DELETE FROM users",
]


@pytest.mark.parametrize("payload", SQL_INJECTION_PAYLOADS)
def test_rejects_sql_injection_payloads(payload):
    with pytest.raises(ValueError, match=INVALID_MESSAGE):
        validate_email(payload)


def test_rejects_emails_over_length_limits():
    with pytest.raises(ValueError, match="Email is too long."):
        validate_email("a" * 65 + "@university.edu")  # local part over 64
    with pytest.raises(ValueError, match="Email is too long."):
        validate_email("a@" + "b" * 250 + ".edu")  # whole address over 254
