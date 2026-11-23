import pytest

from app.wait_time import estimate_smart_wait, estimate_wait


@pytest.mark.parametrize(("people_ahead", "duration_minutes", "expected"), [
    (0, 12, 0),   # First in line: no wait.
    (1, 5, 5),
    (2, 10, 20),  # Third in line: two people ahead.
    (4, 12, 48),
    (100, 480, 48000),
])
def test_estimate_wait(people_ahead, duration_minutes, expected):
    assert estimate_wait(people_ahead, duration_minutes) == expected


@pytest.mark.parametrize("people_ahead", [-1, 1.5, "4", True, None])
def test_rejects_invalid_people_ahead(people_ahead):
    with pytest.raises(ValueError, match="People ahead"):
        estimate_wait(people_ahead, 12)


@pytest.mark.parametrize("duration_minutes", [0, -5, 1.5, "12", True, None])
def test_rejects_invalid_duration(duration_minutes):
    with pytest.raises(ValueError, match="Duration"):
        estimate_wait(4, duration_minutes)


@pytest.mark.parametrize(
    ("people_ahead", "duration", "history", "expected"),
    [
        (0, 12, 20.0, 0),
        (2, 10, None, 20),
        (2, 10, 8.0, 17),
        (4, 12, 60.0, 51),
    ],
)
def test_smart_wait_blends_live_queue_and_recent_history(people_ahead, duration, history, expected):
    assert estimate_smart_wait(people_ahead, duration, history) == expected


@pytest.mark.parametrize("history", [-1, True, "20"])
def test_smart_wait_rejects_invalid_history(history):
    with pytest.raises(ValueError, match="Historical average wait"):
        estimate_smart_wait(2, 12, history)
