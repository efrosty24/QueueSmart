import csv
import io
import sys
from datetime import UTC, date, datetime, timedelta

import pytest

from app import demo_activity
from app.demo_activity import add_demo_activity
from app.queue_store import queues
from app.report_export import date_range_label, filename, to_csv, to_pdf
from app.report_store import ReportFilters, ReportStore

PASSWORD = "Queue$mart1"
START = datetime(2026, 10, 21, 15, tzinfo=UTC)  # a Wednesday, 10 AM in UTC-5


def login(client, email="admin@university.edu"):
    response = client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    return {"Authorization": f"Bearer {response.json()['token']}"}


def csv_sections(text: str) -> dict[str, list[list[str]]]:
    """Splits the stacked CSV into {section title: rows after the title}."""
    assert text.startswith("﻿")
    sections: dict[str, list[list[str]]] = {}
    current = "header"
    for row in csv.reader(io.StringIO(text.lstrip("﻿"))):
        if not row:
            current = None
        elif current is None:
            current = row[0]
            sections[current] = []
        else:
            sections.setdefault(current, []).append(row)
    return sections


@pytest.fixture
def visits(queue_store, patient):
    """Three patients across two services: two served, one left, at known times."""
    store = queue_store
    store.join("svc", "Test svc", 10, patient("ann"), START)
    store.join("svc", "Test svc", 10, patient("bob"), START + timedelta(minutes=5))
    store.serve_next("svc", START + timedelta(minutes=20))  # ann waited 20
    store.serve_next("svc", START + timedelta(minutes=45))  # bob waited 40
    store.join("one", "Test one", 10, patient("cat"), START + timedelta(hours=2))
    store.leave(patient("cat"), START + timedelta(hours=2, minutes=3))
    store.join("two", "Test two", 10, patient("ann"), START + timedelta(days=1))
    store.serve_next("two", START + timedelta(days=1, minutes=30))  # ann waited 30
    store.join("other", "Test other", 10, patient("dan"))  # still waiting
    return ReportStore(store.database.path)


# --- Report data ---------------------------------------------------------------


def test_report_summarizes_usage_services_and_patients(visits):
    report = visits.build(ReportFilters(tz_offset_minutes=300), now=START)
    summary = report.summary
    assert (summary.total_visits, summary.served, summary.left, summary.unique_patients) == (4, 3, 1, 3)
    # Waits count served visits only: (20 + 40 + 30) / 3.
    assert summary.average_wait_minutes == 30.0
    assert summary.longest_wait_minutes == 40
    assert summary.served_rate == 75.0
    assert summary.waiting_now == 1
    # Three of four joins happened 10-11 AM local time (UTC-5).
    assert summary.busiest_hour == 10

    services = {service.service_id: service for service in report.services}
    assert list(services) == ["svc", "one", "two", "other"]
    assert (services["svc"].visits, services["svc"].served, services["svc"].average_wait_minutes) == (2, 2, 30.0)
    assert (services["one"].left, services["one"].average_wait_minutes) == (1, None)
    assert services["other"].waiting_now == 1 and services["other"].visits == 0
    assert services["svc"].status == "open" and not services["svc"].archived

    patients = report.patients
    assert [patient.name for patient in patients] == ["ann", "bob", "cat"]
    ann = patients[0]
    assert (ann.visits, ann.served, ann.average_wait_minutes) == (2, 2, 25.0)
    assert ann.services == ["Test svc", "Test two"]
    assert ann.first_visit_at == START and ann.last_visit_at == START + timedelta(days=1)
    assert report.visits[0].service_id == "two"  # newest first
    assert report.service_name is None


def test_date_filters_use_the_viewers_local_day(visits):
    # 15:00 UTC on Oct 21 is 10 AM in UTC-5 but already Oct 22 in UTC+14.
    oct_21 = date(2026, 10, 21)
    local = visits.build(ReportFilters(start=oct_21, end=oct_21, tz_offset_minutes=300))
    assert local.summary.total_visits == 3
    kiribati = visits.build(ReportFilters(start=oct_21, end=oct_21, tz_offset_minutes=-840))
    assert kiribati.summary.total_visits == 0
    from_next_day = visits.build(ReportFilters(start=oct_21 + timedelta(days=1)))
    assert [visit.service_id for visit in from_next_day.visits] == ["two"]
    through_first_day = visits.build(ReportFilters(end=oct_21))
    assert through_first_day.summary.total_visits == 3


def test_service_filter_limits_visits_services_and_patients(visits):
    report = visits.build(ReportFilters(service_id="one"))
    assert [service.service_id for service in report.services] == ["one"]
    assert [patient.name for patient in report.patients] == ["cat"]
    assert report.service_name == "Test one"
    assert report.summary.busiest_hour == 17  # UTC
    assert visits.service_name("missing") is None


def test_archived_services_appear_only_with_activity(queue_store, visits):
    queue_store.services.archive("one")
    queue_store.services.archive("other")
    queue_store.remove_service("other")
    report = visits.build(ReportFilters(end=date(2026, 10, 21)))
    archived = {service.service_id: service.archived for service in report.services}
    # "other" is archived; dan left when it was removed, but that was today, outside the range.
    assert archived == {"svc": False, "one": True, "two": False}


def test_visits_keep_their_name_when_the_service_row_is_gone(queue_store, visits):
    with queue_store.database.connect() as connection:
        connection.execute("UPDATE History SET service_id = 'retired' WHERE service_id = 'one'")
    service = next(s for s in visits.build(ReportFilters()).services if s.service_id == "retired")
    assert (service.name, service.archived, service.left, service.expected_duration_minutes) == (
        "Test one", True, 1, None)


def test_empty_report_has_no_averages(queue_store):
    report = ReportStore(queue_store.database.path).build(ReportFilters())
    assert report.summary.total_visits == 0
    assert report.summary.average_wait_minutes is None
    assert report.summary.served_rate is None and report.summary.busiest_hour is None
    assert report.patients == [] and report.visits == []


# --- CSV and PDF -----------------------------------------------------------------


def test_csv_has_every_section_in_local_time(visits):
    report = visits.build(ReportFilters(service_id="svc", start=date(2026, 10, 1), tz_offset_minutes=300), now=START)
    sections = csv_sections(to_csv(report))
    assert sections["header"][1:] == [["Generated", "2026-10-21 10:00"], ["Date range", "From 2026-10-01"],
                                      ["Service", "Test svc"]]
    summary = dict(sections["Summary"][1:])
    assert summary["Total visits"] == "2" and summary["Average wait, served (min)"] == "30"
    assert summary["Busiest join hour"] == "10 AM - 11 AM"
    assert sections["Services"][1][:3] == ["Test svc", "Open", "medium"]
    assert [row[0] for row in sections["Patients"][1:]] == ["ann", "bob"]
    assert sections["Visits"][1][4:] == ["2026-10-21 10:05", "2026-10-21 10:45", "Served", "40"]


def test_csv_neutralizes_spreadsheet_formulas(queue_store, patient):
    from app.auth.store import UserStore

    accounts = UserStore(queue_store.database.path)
    user = accounts.create("evil@x.edu", PASSWORD, '=HYPERLINK("http://bad","click")')
    queue_store.join("svc", "Test svc", 10, user.id, START)
    queue_store.serve_next("svc", START)
    text = to_csv(ReportStore(queue_store.database.path).build(ReportFilters()))
    rows = csv_sections(text)["Patients"]
    assert rows[1][0] == "'=HYPERLINK(\"http://bad\",\"click\")"
    assert rows[1][5] == "0"  # numbers are untouched


def test_pdf_is_a_document_even_without_visits(queue_store, visits):
    assert to_pdf(visits.build(ReportFilters())).startswith(b"%PDF")
    empty = ReportStore(queue_store.database.path).build(ReportFilters(start=date(2030, 1, 1)))
    assert to_pdf(empty).startswith(b"%PDF")


@pytest.mark.parametrize(("start", "end", "label"), [
    (None, None, "All dates"),
    (date(2026, 1, 1), None, "From 2026-01-01"),
    (None, date(2026, 2, 1), "Through 2026-02-01"),
    (date(2026, 1, 1), date(2026, 2, 1), "2026-01-01 to 2026-02-01"),
])
def test_date_range_labels(queue_store, start, end, label):
    report = ReportStore(queue_store.database.path).build(ReportFilters(start=start, end=end))
    assert date_range_label(report) == label


def test_filename_uses_the_viewers_date(queue_store):
    store = ReportStore(queue_store.database.path)
    late_evening = datetime(2026, 11, 18, 2, tzinfo=UTC)  # still Nov 17 in UTC-6
    assert filename(store.build(ReportFilters(tz_offset_minutes=360), now=late_evening), "pdf") == \
        "queuesmart-report-2026-11-17.pdf"


# --- API ---------------------------------------------------------------------------


def test_reports_are_admin_only(client):
    assert client.get("/api/reports").status_code == 401
    patient = login(client, "student@university.edu")
    assert client.get("/api/reports", headers=patient).status_code == 403
    assert client.get("/api/reports/export?format=csv", headers=patient).status_code == 403


def test_report_api_reflects_served_patients(client):
    admin = login(client)
    before = client.get("/api/reports", headers=admin).json()
    assert before["summary"]["totalVisits"] == 0
    assert before["summary"]["waitingNow"] == 6  # the seeded demo patients
    assert [service["serviceId"] for service in before["services"]] == [
        "sick-visit", "flu-shot", "prescription-refill", "lab-work"]

    served = client.post("/api/queues/sick-visit/serve-next", headers=admin).json()["served"]
    report = client.get("/api/reports", headers=admin, params={"serviceId": "sick-visit"}).json()
    assert report["serviceName"] == "Sick Visit"
    assert report["summary"]["served"] == 1 and report["summary"]["waitingNow"] == 3
    assert report["visits"][0]["ticket"] == served["ticket"]
    assert report["visits"][0]["patientName"] == "Jordan Lee"
    assert report["patients"][0]["email"] == "jordan.lee@university.edu"
    assert report["filters"] == {"start": None, "end": None, "serviceId": "sick-visit"}


def test_report_api_validates_filters(client):
    admin = login(client)
    backwards = client.get("/api/reports", headers=admin, params={"start": "2026-11-10", "end": "2026-11-01"})
    assert backwards.status_code == 422
    assert backwards.json()["detail"] == "The start date must be on or before the end date."
    assert client.get("/api/reports", headers=admin, params={"serviceId": "nope"}).status_code == 404
    assert client.get("/api/reports", headers=admin, params={"tzOffset": 900}).status_code == 422
    assert client.get("/api/reports", headers=admin, params={"start": "yesterday"}).status_code == 422
    assert client.get("/api/reports/export", headers=admin, params={"format": "xlsx"}).status_code == 422
    # An empty service filter means all services.
    assert client.get("/api/reports", headers=admin, params={"serviceId": ""}).status_code == 200


def test_exports_download_as_files(client):
    admin = login(client)
    client.post("/api/queues/flu-shot/serve-next", headers=admin)

    csv_response = client.get("/api/reports/export", headers=admin, params={"tzOffset": 0})
    assert csv_response.status_code == 200
    assert csv_response.headers["content-type"] == "text/csv; charset=utf-8"
    assert csv_response.headers["content-disposition"].startswith('attachment; filename="queuesmart-report-')
    assert csv_response.headers["cache-control"] == "no-store"
    assert csv_sections(csv_response.text)["Visits"][1][1] == "Avery Patel"

    pdf_response = client.get("/api/reports/export", headers=admin, params={"format": "pdf", "serviceId": "flu-shot"})
    assert pdf_response.status_code == 200
    assert pdf_response.headers["content-type"] == "application/pdf"
    assert pdf_response.headers["content-disposition"].endswith('.pdf"')
    assert pdf_response.content.startswith(b"%PDF")


# --- Demo data -------------------------------------------------------------------------


def test_demo_activity_fills_weekdays_once(queue_store, patient):
    waiting = queue_store.join("svc", "Test svc", 10, patient("waiting"))
    now = datetime(2026, 11, 17, 18, tzinfo=UTC)  # a Tuesday
    added = add_demo_activity(queue_store, days=7, now=now)
    assert added > 0
    assert add_demo_activity(queue_store, days=7, now=now) == 0
    assert add_demo_activity(queue_store, days=1, now=now, force=True) > 0

    report = ReportStore(queue_store.database.path).build(ReportFilters())
    assert report.summary.total_visits > added
    # The clinic is closed on weekends (in the server's local time, which the script uses).
    local_offset = datetime.now().astimezone().utcoffset()
    assert all((visit.joined_at + local_offset).weekday() < 5 for visit in report.visits)
    assert all(visit.joined_at < now for visit in report.visits)
    assert {patient.email.split("@")[0].split(".")[0] for patient in report.patients} == {"demo"}
    # Patients waiting right now are left alone.
    assert queue_store.get(waiting.id).status == "waiting"
    assert queue_store.current_for(patient("waiting")).id == waiting.id


def test_demo_activity_skips_weekends(queue_store):
    # Noon UTC is Monday, Nov 16 in every time zone from UTC-11 to UTC+11, so the two days
    # before it are Saturday and Sunday.
    monday = datetime(2026, 11, 16, 12, tzinfo=UTC)
    assert add_demo_activity(queue_store, days=2, now=monday) == 0
    assert add_demo_activity(queue_store, days=3, now=monday) > 0  # adds Friday


def test_demo_activity_needs_services(tmp_path):
    from app.queue_store import QueueStore

    assert add_demo_activity(QueueStore(tmp_path / "empty.sqlite3")) == 0


def test_demo_activity_command(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["demo_activity", "--days", "3"])
    demo_activity.main()
    assert "past visits" in capsys.readouterr().out
    demo_activity.main()
    assert "nothing was added" in capsys.readouterr().out
    assert queues.history.for_user(queues.waiting("sick-visit")[0].user_id) == []
