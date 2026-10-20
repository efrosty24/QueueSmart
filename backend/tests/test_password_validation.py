import pytest

from app.auth.validation import (
    PASSWORD_MAX_LENGTH,
    validate_login_password,
    validate_new_password,
)


@pytest.mark.parametrize("password", ["Queue$mart", "ABCDEFG!", "Pa ss-word", "Ünïcødé#A", "A" * 63 + "!"])
def test_new_password_accepts_valid_passwords(password):
    assert validate_new_password(password) == password


@pytest.mark.parametrize(
    ("password", "message"),
    [
        ("", "Password is required."),
        ("Ab!4567", "Use at least 8 characters."),
        ("queue$mart", "Include at least one uppercase letter."),
        ("QueueSmart1", "Include at least one special character"),
        ("Queue Smart", "Include at least one special character"),  # a space is not special
        ("A!" + "a" * (PASSWORD_MAX_LENGTH - 1), f"Use at most {PASSWORD_MAX_LENGTH} characters."),
    ],
)
def test_new_password_rejects_with_message(password, message):
    with pytest.raises(ValueError, match=message):
        validate_new_password(password)


def test_new_password_rejects_multibyte_password_over_bcrypt_limit():
    # 38 characters (under the limit), but each "é" is 2 bytes in UTF-8: 2 + 2 * 36 = 74 bytes.
    password = "A!" + "é" * 36
    assert len(password) <= PASSWORD_MAX_LENGTH

    with pytest.raises(ValueError, match="Use at most"):
        validate_new_password(password)


def test_login_password_only_checks_presence_and_length():
    # Weak passwords are fine at login; strength is enforced when the account is created.
    assert validate_login_password("short") == "short"

    with pytest.raises(ValueError, match="Password is required."):
        validate_login_password("")
    with pytest.raises(ValueError, match="Use at most"):
        validate_login_password("x" * (PASSWORD_MAX_LENGTH + 1))
