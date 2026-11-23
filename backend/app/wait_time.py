"""Smart wait estimates shared by service previews and queue endpoints."""


def estimate_wait(people_ahead: int, duration_minutes: int) -> int:
    """Return minutes to wait. For a queued user, people_ahead is position - 1."""
    if type(people_ahead) is not int or people_ahead < 0:
        raise ValueError("People ahead must be a non-negative whole number.")
    if type(duration_minutes) is not int or duration_minutes <= 0:
        raise ValueError("Duration must be a positive whole number of minutes.")
    return people_ahead * duration_minutes


def estimate_smart_wait(
    people_ahead: int,
    duration_minutes: int,
    historical_average_wait: float | None = None,
) -> int:
    """Blend the live queue estimate with recent served-wait history.

    The live estimate remains the strongest signal, while recent history calibrates
    it for services that consistently run faster or slower than their configured
    typical duration. A patient at the front of the line still has no queue wait.
    """
    live_estimate = estimate_wait(people_ahead, duration_minutes)
    if historical_average_wait is None or people_ahead == 0:
        return live_estimate
    if isinstance(historical_average_wait, bool) or not isinstance(historical_average_wait, (int, float)):
        raise ValueError("Historical average wait must be a non-negative number of minutes.")
    if historical_average_wait < 0:
        raise ValueError("Historical average wait must be a non-negative number of minutes.")

    # Keep the current queue as the primary signal and use history as calibration.
    return round(live_estimate * 0.75 + historical_average_wait * 0.25)
