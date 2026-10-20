import pytest

from app.wait_time import estimate_wait


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
