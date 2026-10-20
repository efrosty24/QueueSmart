from app.auth.passwords import BCRYPT_ROUNDS, hash_password, verify_password


def test_hash_is_bcrypt_and_not_plain_text():
    password_hash = hash_password("Queue$mart1")

    assert password_hash != "Queue$mart1"
    assert password_hash.startswith(f"$2b${BCRYPT_ROUNDS:02d}$")


def test_same_password_gets_a_different_salt_each_time():
    assert hash_password("Queue$mart1") != hash_password("Queue$mart1")


def test_verify_accepts_the_right_password():
    password_hash = hash_password("Queue$mart1")

    assert verify_password("Queue$mart1", password_hash) is True


def test_verify_rejects_wrong_password():
    password_hash = hash_password("Queue$mart1")

    assert verify_password("queue$mart1", password_hash) is False
    assert verify_password("", password_hash) is False


def test_verify_returns_false_for_malformed_hash():
    assert verify_password("Queue$mart1", "not-a-bcrypt-hash") is False


def test_verify_returns_false_for_password_over_bcrypt_limit():
    password_hash = hash_password("Queue$mart1")

    assert verify_password("x" * 100, password_hash) is False
