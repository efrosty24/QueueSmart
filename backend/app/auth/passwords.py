"""Password hashing with bcrypt. Plain-text passwords are never stored."""

import os

import bcrypt

# Cost factor: each +1 doubles the work. 12 is bcrypt's standard default; tests
# lower it through the environment so the suite stays fast.
BCRYPT_ROUNDS = int(os.environ.get("QUEUESMART_BCRYPT_ROUNDS", "12"))


def hash_password(password: str) -> str:
    """Returns a salted bcrypt hash like "$2b$12$...". The salt is stored inside the hash."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=BCRYPT_ROUNDS)).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    """Constant-time check of a password against a stored hash."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("ascii"))
    except ValueError:
        # Malformed hash, or a password over bcrypt's 72-byte limit.
        return False


# Checked against when an email isn't registered, so a login for an unknown
# account takes as long as one with a wrong password (no account enumeration by timing).
DUMMY_HASH = hash_password("not-a-real-password")
