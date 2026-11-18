"""Adds past clinic visits to the database so reports have history to show in a demo.

    python -m app.demo_activity            # 14 days of visits, once
    python -m app.demo_activity --days 30  # a longer stretch
    python -m app.demo_activity --force    # add more even if visits are already saved

Visits are saved as finished queue entries plus History rows, like real ones. They use
their own demo patient accounts (password Queue$mart1), so patients waiting right now
and the demo student's account are left alone. No notifications are created for them.
It never runs on its own: normal startup and the tests don't call it.
"""

import argparse
import random
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from .auth.store import SEED_PASSWORD, EmailTakenError, UserStore
from .queue_store import QueueStore, queues

DEMO_PATIENTS = (
    "Jamie Rivera", "Sam Okafor", "Priya Nair", "Diego Alvarez", "Mei Tanaka", "Noah Bennett",
    "Aisha Rahman", "Lucas Moreau", "Hannah Schultz", "Omar Haddad", "Grace Liu", "Ethan Walker",
)

# Busier in the late morning and right after lunch, as at a campus clinic.
_HOURLY_WEIGHTS = {9: 3, 10: 5, 11: 6, 12: 3, 13: 5, 14: 4, 15: 3, 16: 2}
# Share of patients who leave instead of being served.
_LEAVE_RATE = 0.12


def _demo_accounts(store: QueueStore) -> list[str]:
    accounts = UserStore(store.database.path)
    ids = []
    for name in DEMO_PATIENTS:
        email = f"demo.{name.lower().replace(' ', '.')}@university.edu"
        try:
            ids.append(accounts.create(email, SEED_PASSWORD, name).id)
        except EmailTakenError:
            ids.append(accounts.get_by_email(email).id)
    return ids


def add_demo_activity(store: QueueStore, *, days: int = 14, now: datetime | None = None,
                      seed: int = 2026, force: bool = False) -> int:
    """Saves finished visits for the past `days` days and returns how many were added.
    Adds nothing when visits are already saved, unless force is set."""
    now = now or datetime.now(UTC)
    rng = random.Random(seed)
    with store.database.connect() as connection:
        if not force and connection.execute("SELECT 1 FROM History LIMIT 1").fetchone():
            return 0
    patients = _demo_accounts(store)
    services = store.services.list()
    if not services:
        return 0
    hours, weights = zip(*_HOURLY_WEIGHTS.items())
    local_offset = datetime.now().astimezone().utcoffset() or timedelta()
    added = 0
    with store.database.connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        arrival = connection.execute("SELECT coalesce(max(arrival), 0) FROM QueueEntry").fetchone()[0]
        for days_ago in range(days, 0, -1):
            day = (now + local_offset - timedelta(days=days_ago)).date()
            if day.weekday() >= 5:  # the clinic is closed on weekends
                continue
            for service in services:
                # Queues need a row before entries can reference them.
                connection.execute(
                    "INSERT INTO Queue (queue_id, service_id, status, created_at) VALUES (?, ?, 'open', ?) "
                    "ON CONFLICT (service_id) DO NOTHING", (str(uuid4()), service.id, now.isoformat()),
                )
                queue_id = connection.execute(
                    "SELECT queue_id FROM Queue WHERE service_id = ?", (service.id,),
                ).fetchone()[0]
                for _ in range(rng.randint(2, 6)):
                    local_join = datetime.combine(day, datetime.min.time()) + timedelta(
                        hours=rng.choices(hours, weights)[0], minutes=rng.randrange(60))
                    joined_at = (local_join - local_offset).replace(tzinfo=UTC)
                    left = rng.random() < _LEAVE_RATE
                    # Waits grow with how long the service takes, with some variation.
                    waited = rng.randint(1, 8) if left else max(
                        1, round(service.expected_duration_minutes * rng.uniform(0.5, 3.0)))
                    finished_at = joined_at + timedelta(minutes=waited, seconds=rng.randrange(60))
                    user_id = rng.choice(patients)
                    arrival += 1
                    entry_id = str(uuid4())
                    ticket = f"{service.name[:1].upper()}-{arrival:03d}"
                    outcome = "left" if left else "served"
                    connection.execute(
                        "INSERT INTO QueueEntry (entry_id, queue_id, user_id, arrival, ticket, position, joined_at, "
                        "status, finished_at, service_name, duration_minutes) "
                        "VALUES (?, ?, ?, ?, ?, NULL, ?, ?, ?, ?, ?)",
                        (entry_id, queue_id, user_id, arrival, ticket, joined_at.isoformat(), outcome,
                         finished_at.isoformat(), service.name, service.expected_duration_minutes),
                    )
                    store.history.record(
                        entry_id=entry_id, user_id=user_id, ticket=ticket, service_id=service.id,
                        service_name=service.name, joined_at=joined_at, finished_at=finished_at,
                        outcome=outcome, connection=connection,
                    )
                    added += 1
    return added


def main() -> None:
    parser = argparse.ArgumentParser(description="Add past clinic visits for report demos.")
    parser.add_argument("--days", type=int, default=14, help="how many past days to fill (default 14)")
    parser.add_argument("--force", action="store_true", help="add visits even if some are already saved")
    args = parser.parse_args()
    # The app's own database (QUEUESMART_DATABASE_PATH).
    added = add_demo_activity(queues, days=args.days, force=args.force)
    if added:
        print(f"Added {added} past visits to {queues.database.path}.")
    else:
        print("Visits are already saved, so nothing was added. Use --force to add more.")


if __name__ == "__main__":
    main()
