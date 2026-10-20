"""Input rules for the auth endpoints.

Each validator returns the cleaned value or raises ValueError with a message
that is safe to show to the user. The frontend mirrors these rules in
frontend/src/features/auth/validation.ts; keep the two in sync.
"""

import re

EMAIL_MAX_LENGTH = 254
EMAIL_LOCAL_MAX_LENGTH = 64

# The email doubles as the username. This is an allowlist: only characters that
# appear in normal addresses are accepted, so quotes, semicolons, equals signs,
# spaces, slashes and asterisks (what SQL injection payloads need) can never get
# through. There is no database yet, but A4 adds one and this rule keeps the
# username field safe as defense in depth alongside parameterized queries.
_EMAIL = re.compile(
    r"^[a-z0-9._%+-]+"                # local part
    r"@[a-z0-9](?:[a-z0-9-]*[a-z0-9])?"  # first domain label
    r"(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)*"  # more labels
    r"\.[a-z]{2,}$"                    # top-level domain
)
# Sequences built only from allowed characters that still have special meaning:
# "--" starts an SQL comment, ".." is never valid in an address.
_FORBIDDEN_SEQUENCES = ("--", "..")

PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 64
# bcrypt only uses the first 72 bytes of a password (and bcrypt 5 rejects longer
# input), so multi-byte characters must not push a password past this.
PASSWORD_MAX_BYTES = 72

_UPPERCASE = re.compile(r"[A-Z]")
# Anything that isn't a letter, digit or whitespace counts as special: ! # $ % & * @ ...
_SPECIAL = re.compile(r"[^A-Za-z0-9\s]")


def validate_email(email: str) -> str:
    """Normalizes (trim + lowercase) and checks an email/username."""
    value = email.strip().lower()
    if not value:
        raise ValueError("Email is required.")
    if len(value) > EMAIL_MAX_LENGTH or len(value.split("@", 1)[0]) > EMAIL_LOCAL_MAX_LENGTH:
        raise ValueError("Email is too long.")
    if not _EMAIL.fullmatch(value) or any(seq in value for seq in _FORBIDDEN_SEQUENCES):
        raise ValueError("Enter a valid email address, like name@university.edu.")
    return value


def _check_password_length(password: str) -> None:
    if len(password) > PASSWORD_MAX_LENGTH or len(password.encode("utf-8")) > PASSWORD_MAX_BYTES:
        raise ValueError(f"Use at most {PASSWORD_MAX_LENGTH} characters.")


def validate_new_password(password: str) -> str:
    """Strength rules for registration."""
    if not password:
        raise ValueError("Password is required.")
    if len(password) < PASSWORD_MIN_LENGTH:
        raise ValueError(f"Use at least {PASSWORD_MIN_LENGTH} characters.")
    _check_password_length(password)
    if not _UPPERCASE.search(password):
        raise ValueError("Include at least one uppercase letter.")
    if not _SPECIAL.search(password):
        raise ValueError("Include at least one special character, like ! or #.")
    return password


def validate_login_password(password: str) -> str:
    """Login only checks presence and length; strength rules apply at sign-up."""
    if not password:
        raise ValueError("Password is required.")
    _check_password_length(password)
    return password
