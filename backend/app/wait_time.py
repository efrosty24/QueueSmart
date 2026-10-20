"""Basic wait estimates shared by service previews and future queue endpoints."""


def estimate_wait(people_ahead: int, duration_minutes: int) -> int:
    """Return minutes to wait. For a queued user, people_ahead is position - 1."""
    if type(people_ahead) is not int or people_ahead < 0:
        raise ValueError("People ahead must be a non-negative whole number.")
    if type(duration_minutes) is not int or duration_minutes <= 0:
        raise ValueError("Duration must be a positive whole number of minutes.")
    return people_ahead * duration_minutes
