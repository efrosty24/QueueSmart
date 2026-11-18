"""Admin reports (Final project): queue participation, service activity and usage statistics.

Reports are read-only views over the saved queue data:
- History: every finished visit (served or left), with its join/finish times and minutes waited
- UserProfile / UserCredentials: who each visit belongs to
- Service / Queue / QueueEntry: service details, open/closed status and who is waiting now

Filters pick visits by the date the patient joined the queue, in the viewer's local time.
"""

import sqlite3
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from typing import Literal

from .database import Database, database_path


@dataclass(frozen=True)
class ReportFilters:
    # Inclusive local dates. None means no limit on that side.
    start: date | None = None
    end: date | None = None
    service_id: str | None = None
    # Minutes to add to local time to get UTC (JavaScript's Date.getTimezoneOffset()).
    tz_offset_minutes: int = 0

    def utc_range(self) -> tuple[datetime | None, datetime | None]:
        """[start, end) in UTC: local midnight at the start, local midnight after the end date."""
        offset = timedelta(minutes=self.tz_offset_minutes)
        start = datetime.combine(self.start, time.min, UTC) + offset if self.start else None
        end = datetime.combine(self.end + timedelta(days=1), time.min, UTC) + offset if self.end else None
        return start, end

    def local(self, moment: datetime) -> datetime:
        """A stored UTC time as the viewer's wall-clock time (no time zone attached)."""
        return (moment.astimezone(UTC) - timedelta(minutes=self.tz_offset_minutes)).replace(tzinfo=None)


@dataclass(frozen=True)
class ReportVisit:
    id: str
    ticket: str
    user_id: str
    patient_name: str
    email: str
    service_id: str
    service_name: str
    joined_at: datetime
    finished_at: datetime
    outcome: Literal["served", "left"]
    waited_minutes: int


@dataclass
class ServiceActivity:
    service_id: str
    name: str
    description: str
    expected_duration_minutes: int | None
    priority: str | None
    status: Literal["open", "closed"]
    archived: bool
    waiting_now: int
    visits: int = 0
    served: int = 0
    left: int = 0
    average_wait_minutes: float | None = None
    longest_wait_minutes: int | None = None


@dataclass
class PatientActivity:
    user_id: str
    name: str
    email: str
    visits: int = 0
    served: int = 0
    left: int = 0
    average_wait_minutes: float | None = None
    first_visit_at: datetime | None = None
    last_visit_at: datetime | None = None
    services: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ReportSummary:
    total_visits: int
    served: int
    left: int
    unique_patients: int
    # Wait times count served visits only: patients who left never finished waiting.
    average_wait_minutes: float | None
    longest_wait_minutes: int | None
    # Share of finished visits that were served, as a percentage.
    served_rate: float | None
    waiting_now: int
    # Local hour (0-23) when the most patients joined a queue.
    busiest_hour: int | None


@dataclass(frozen=True)
class Report:
    generated_at: datetime
    filters: ReportFilters
    service_name: str | None
    summary: ReportSummary
    services: list[ServiceActivity]
    patients: list[PatientActivity]
    # Newest first.
    visits: list[ReportVisit]


_VISIT_QUERY = """
    SELECT h.entry_id, h.ticket, h.user_id, coalesce(p.full_name, c.email) AS patient_name, c.email,
           h.service_id, h.service_name, h.joined_at, h.finished_at, h.outcome, h.waited_minutes
    FROM History AS h
    JOIN UserCredentials AS c ON c.user_id = h.user_id
    LEFT JOIN UserProfile AS p ON p.email = c.email
    WHERE (:start IS NULL OR julianday(h.joined_at) >= julianday(:start))
      AND (:end IS NULL OR julianday(h.joined_at) < julianday(:end))
      AND (:service_id IS NULL OR h.service_id = :service_id)
    ORDER BY julianday(h.joined_at) DESC, h.rowid DESC
"""

# Every service (active first, then archived), its queue status and how many people wait now.
_SERVICE_QUERY = """
    SELECT s.service_id, s.name, s.description, s.expected_duration_minutes, s.priority,
           s.deleted_at IS NOT NULL AS archived, coalesce(q.status, 'closed') AS status,
           (SELECT count(*) FROM QueueEntry AS e WHERE e.queue_id = q.queue_id AND e.status = 'waiting') AS waiting
    FROM Service AS s
    LEFT JOIN Queue AS q ON q.service_id = s.service_id
    WHERE (:service_id IS NULL OR s.service_id = :service_id)
    ORDER BY archived, s.created_at, s.rowid
"""


def _average(values: list[int]) -> float | None:
    return round(sum(values) / len(values), 1) if values else None


def _visit(row: sqlite3.Row) -> ReportVisit:
    return ReportVisit(
        id=row["entry_id"], ticket=row["ticket"], user_id=row["user_id"], patient_name=row["patient_name"],
        email=row["email"], service_id=row["service_id"], service_name=row["service_name"],
        joined_at=datetime.fromisoformat(row["joined_at"]), finished_at=datetime.fromisoformat(row["finished_at"]),
        outcome=row["outcome"], waited_minutes=row["waited_minutes"],
    )


def _service_stats(service: ServiceActivity, visits: list[ReportVisit]) -> None:
    waits = [visit.waited_minutes for visit in visits if visit.outcome == "served"]
    service.visits = len(visits)
    service.served = len(waits)
    service.left = service.visits - service.served
    service.average_wait_minutes = _average(waits)
    service.longest_wait_minutes = max(waits, default=None)


def _patients(visits: list[ReportVisit]) -> list[PatientActivity]:
    by_user: dict[str, list[ReportVisit]] = defaultdict(list)
    for visit in visits:
        by_user[visit.user_id].append(visit)
    patients = []
    for user_id, history in by_user.items():
        waits = [visit.waited_minutes for visit in history if visit.outcome == "served"]
        # Services in the order the patient first used them; history is newest first.
        services = list(dict.fromkeys(visit.service_name for visit in reversed(history)))
        patients.append(PatientActivity(
            user_id=user_id, name=history[0].patient_name, email=history[0].email,
            visits=len(history), served=len(waits), left=len(history) - len(waits),
            average_wait_minutes=_average(waits),
            first_visit_at=history[-1].joined_at, last_visit_at=history[0].joined_at, services=services,
        ))
    # Most active patients first, then alphabetical.
    patients.sort(key=lambda patient: (-patient.visits, patient.name.lower(), patient.email))
    return patients


class ReportStore:
    def __init__(self, path: str | Path | None = None) -> None:
        self.database = Database(path if path is not None else database_path())

    def service_name(self, service_id: str) -> str | None:
        """Any saved service's name, including archived ones (past reports still cover them)."""
        with self.database.connect() as connection:
            row = connection.execute("SELECT name FROM Service WHERE service_id = ?", (service_id,)).fetchone()
        return row["name"] if row else None

    def build(self, filters: ReportFilters, now: datetime | None = None) -> Report:
        start, end = filters.utc_range()
        params = {
            "start": start.isoformat() if start else None,
            "end": end.isoformat() if end else None,
            "service_id": filters.service_id,
        }
        with self.database.connect() as connection:
            visits = [_visit(row) for row in connection.execute(_VISIT_QUERY, params)]
            service_rows = connection.execute(_SERVICE_QUERY, {"service_id": filters.service_id}).fetchall()

        by_service: dict[str, list[ReportVisit]] = defaultdict(list)
        for visit in visits:
            by_service[visit.service_id].append(visit)

        services = []
        for row in service_rows:
            # Archived services only matter when they had activity in the report's range.
            if row["archived"] and row["service_id"] not in by_service:
                continue
            service = ServiceActivity(
                service_id=row["service_id"], name=row["name"], description=row["description"],
                expected_duration_minutes=row["expected_duration_minutes"], priority=row["priority"],
                status=row["status"], archived=bool(row["archived"]), waiting_now=row["waiting"],
            )
            _service_stats(service, by_service.get(service.service_id, []))
            services.append(service)
        # History keeps a copy of the service name, so visits whose service row is gone still count.
        known = {service.service_id for service in services}
        for service_id, history in by_service.items():
            if service_id not in known:
                service = ServiceActivity(
                    service_id=service_id, name=history[0].service_name, description="",
                    expected_duration_minutes=None, priority=None, status="closed", archived=True, waiting_now=0,
                )
                _service_stats(service, history)
                services.append(service)

        waits = [visit.waited_minutes for visit in visits if visit.outcome == "served"]
        hours = Counter(filters.local(visit.joined_at).hour for visit in visits)
        summary = ReportSummary(
            total_visits=len(visits), served=len(waits), left=len(visits) - len(waits),
            unique_patients=len({visit.user_id for visit in visits}),
            average_wait_minutes=_average(waits), longest_wait_minutes=max(waits, default=None),
            served_rate=round(100 * len(waits) / len(visits), 1) if visits else None,
            waiting_now=sum(service.waiting_now for service in services),
            # Ties go to the earlier hour.
            busiest_hour=min(hours, key=lambda hour: (-hours[hour], hour)) if hours else None,
        )
        return Report(
            generated_at=now or datetime.now(UTC), filters=filters,
            service_name=self.service_name(filters.service_id) if filters.service_id else None,
            summary=summary, services=services, patients=_patients(visits), visits=visits,
        )
