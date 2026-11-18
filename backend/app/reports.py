"""Admin reporting module (Final project).

GET /api/reports          the report as JSON, for the admin reports page
GET /api/reports/export   the same report as a CSV or PDF download

Both are administrator-only and take the same optional filters: start/end (inclusive
local dates, matched against when the patient joined the queue), serviceId, and
tzOffset (the browser's Date.getTimezoneOffset(), so dates and times match the viewer's clock).
"""

from datetime import date, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from .auth.dependencies import require_admin
from .queue_store import queues
from .report_export import filename, to_csv, to_pdf
from .report_store import ReportFilters, ReportStore

# The same database as the queues, so reports see every saved visit.
reports = ReportStore(queues.database.path)


class _View(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, validate_by_name=True, from_attributes=True)


class ReportFiltersView(_View):
    start: date | None
    end: date | None
    service_id: str | None


class ReportSummaryView(_View):
    total_visits: int
    served: int
    left: int
    unique_patients: int
    average_wait_minutes: float | None
    longest_wait_minutes: int | None
    served_rate: float | None
    waiting_now: int
    busiest_hour: int | None


class ServiceActivityView(_View):
    service_id: str
    name: str
    description: str
    expected_duration_minutes: int | None
    priority: str | None
    status: Literal["open", "closed"]
    archived: bool
    waiting_now: int
    visits: int
    served: int
    left: int
    average_wait_minutes: float | None
    longest_wait_minutes: int | None


class PatientActivityView(_View):
    user_id: str
    name: str
    email: str
    visits: int
    served: int
    left: int
    average_wait_minutes: float | None
    first_visit_at: datetime | None
    last_visit_at: datetime | None
    services: list[str]


class ReportVisitView(_View):
    id: str
    ticket: str
    patient_name: str
    email: str
    service_id: str
    service_name: str
    joined_at: datetime
    finished_at: datetime
    outcome: Literal["served", "left"]
    waited_minutes: int


class ReportView(_View):
    generated_at: datetime
    filters: ReportFiltersView
    service_name: str | None
    summary: ReportSummaryView
    services: list[ServiceActivityView]
    patients: list[PatientActivityView]
    visits: list[ReportVisitView]


router = APIRouter(prefix="/api/reports", tags=["reports"], dependencies=[Depends(require_admin)])


def report_filters(
    start: Annotated[date | None, Query()] = None,
    end: Annotated[date | None, Query()] = None,
    service_id: Annotated[str | None, Query(alias="serviceId", max_length=100)] = None,
    # Real UTC offsets run from -14:00 to +14:00.
    tz_offset: Annotated[int, Query(alias="tzOffset", ge=-840, le=840)] = 0,
) -> ReportFilters:
    if start and end and start > end:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "The start date must be on or before the end date.")
    service_id = service_id or None
    if service_id and reports.service_name(service_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Service not found.")
    return ReportFilters(start=start, end=end, service_id=service_id, tz_offset_minutes=tz_offset)


Filters = Annotated[ReportFilters, Depends(report_filters)]


@router.get("")
def get_report(filters: Filters) -> ReportView:
    return ReportView.model_validate(reports.build(filters))


@router.get("/export")
def export_report(filters: Filters, format: Annotated[Literal["csv", "pdf"], Query()] = "csv") -> Response:
    report = reports.build(filters)
    if format == "pdf":
        content, media_type = to_pdf(report), "application/pdf"
    else:
        content, media_type = to_csv(report).encode("utf-8"), "text/csv; charset=utf-8"
    return Response(
        content=content, media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename(report, format)}"',
            # Reports hold patient details: don't let browsers or proxies keep copies.
            "Cache-Control": "no-store",
        },
    )
