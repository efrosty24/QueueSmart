"""CSV and PDF downloads of an admin report (report_store.Report).

Both formats hold the same four sections: summary, services, patients and visits.
Times are shown in the viewer's local time, the same as the reports page.
"""

import csv
import io
from datetime import datetime
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .report_store import Report

# Spreadsheet apps run cells starting with these as formulas; patient names are user input.
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _cell(value: object) -> object:
    if value is None:
        return ""
    if isinstance(value, str) and value.startswith(_FORMULA_PREFIXES):
        return "'" + value
    return value


def _when(report: Report, moment: datetime | None) -> str:
    return report.filters.local(moment).strftime("%Y-%m-%d %H:%M") if moment else ""


def _minutes(value: float | int | None) -> str:
    return "" if value is None else f"{value:g}"


def _hour(hour: int | None) -> str:
    if hour is None:
        return ""
    end = (hour + 1) % 24
    return f"{hour % 12 or 12} {'AM' if hour < 12 else 'PM'} - {end % 12 or 12} {'AM' if end < 12 else 'PM'}"


def date_range_label(report: Report) -> str:
    start, end = report.filters.start, report.filters.end
    if start and end:
        return f"{start.isoformat()} to {end.isoformat()}"
    if start:
        return f"From {start.isoformat()}"
    if end:
        return f"Through {end.isoformat()}"
    return "All dates"


def filename(report: Report, extension: str) -> str:
    return f"queuesmart-report-{report.filters.local(report.generated_at):%Y-%m-%d}.{extension}"


def _summary_rows(report: Report) -> list[tuple[str, str]]:
    summary = report.summary
    return [
        ("Total visits", str(summary.total_visits)),
        ("Patients served", str(summary.served)),
        ("Left the queue", str(summary.left)),
        ("Unique patients", str(summary.unique_patients)),
        ("Served rate (%)", _minutes(summary.served_rate)),
        ("Average wait, served (min)", _minutes(summary.average_wait_minutes)),
        ("Longest wait, served (min)", _minutes(summary.longest_wait_minutes)),
        ("Busiest join hour", _hour(summary.busiest_hour)),
        ("Waiting now", str(summary.waiting_now)),
    ]


_SERVICE_HEADER = ("Service", "Status", "Priority", "Expected min", "Waiting now", "Visits", "Served", "Left",
                   "Avg wait (min)", "Longest wait (min)")
_PATIENT_HEADER = ("Patient", "Email", "Visits", "Served", "Left", "Avg wait (min)", "First visit", "Last visit",
                   "Services used")
_VISIT_HEADER = ("Ticket", "Patient", "Email", "Service", "Joined", "Finished", "Outcome", "Waited (min)")


def _service_status(service) -> str:
    return "Archived" if service.archived else service.status.title()


def to_csv(report: Report) -> str:
    output = io.StringIO()
    # The byte order mark makes Excel read the file as UTF-8, so accented names display correctly.
    output.write("﻿")
    writer = csv.writer(output, lineterminator="\n")

    def rows(*lines) -> None:
        writer.writerows([[_cell(value) for value in line] for line in lines])

    rows(("QueueSmart report",),
         ("Generated", _when(report, report.generated_at)),
         ("Date range", date_range_label(report)),
         ("Service", report.service_name or "All services"),
         (), ("Summary",), ("Metric", "Value"), *_summary_rows(report))
    rows((), ("Services",), _SERVICE_HEADER, *[
        (s.name, _service_status(s), s.priority, s.expected_duration_minutes, s.waiting_now, s.visits, s.served,
         s.left, _minutes(s.average_wait_minutes), _minutes(s.longest_wait_minutes))
        for s in report.services
    ])
    rows((), ("Patients",), _PATIENT_HEADER, *[
        (p.name, p.email, p.visits, p.served, p.left, _minutes(p.average_wait_minutes),
         _when(report, p.first_visit_at), _when(report, p.last_visit_at), "; ".join(p.services))
        for p in report.patients
    ])
    rows((), ("Visits",), _VISIT_HEADER, *[
        (v.ticket, v.patient_name, v.email, v.service_name, _when(report, v.joined_at),
         _when(report, v.finished_at), v.outcome.title(), v.waited_minutes)
        for v in report.visits
    ])
    return output.getvalue()


# --- PDF ---------------------------------------------------------------------

_BRAND = colors.HexColor("#b91c1c")
_MUTED = colors.HexColor("#52525b")
_STRIPE = colors.HexColor("#f4f4f5")
_GRID = colors.HexColor("#d4d4d8")


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("title", parent=base["Title"], alignment=0, textColor=_BRAND, spaceAfter=4),
        "meta": ParagraphStyle("meta", parent=base["Normal"], textColor=_MUTED, fontSize=9, leading=12),
        "heading": ParagraphStyle("heading", parent=base["Heading2"], spaceBefore=14, spaceAfter=6),
        "cell": ParagraphStyle("cell", parent=base["Normal"], fontSize=8, leading=10),
        "empty": ParagraphStyle("empty", parent=base["Normal"], textColor=_MUTED, fontSize=9),
    }


def _table(header: tuple[str, ...], body: list[list], widths: list[float], styles) -> Table:
    # Paragraph cells wrap long names and emails. Escape them: Paragraph reads its text as markup.
    def wrap(value: object) -> object:
        return Paragraph(escape(value), styles["cell"]) if isinstance(value, str) else value

    data = [list(header)] + [[wrap(value if value is not None else "") for value in row] for row in body]
    table = Table(data, colWidths=widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), _BRAND),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _STRIPE]),
        ("LINEBELOW", (0, 0), (-1, -1), 0.25, _GRID),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


def _page_number(canvas, document) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(_MUTED)
    canvas.drawRightString(document.pagesize[0] - document.rightMargin, 0.4 * inch, f"Page {document.page}")
    canvas.drawString(document.leftMargin, 0.4 * inch, "QueueSmart - confidential clinic report")
    canvas.restoreState()


def to_pdf(report: Report) -> bytes:
    buffer = io.BytesIO()
    document = SimpleDocTemplate(
        buffer, pagesize=landscape(letter), title="QueueSmart report", author="QueueSmart",
        leftMargin=0.5 * inch, rightMargin=0.5 * inch, topMargin=0.5 * inch, bottomMargin=0.7 * inch,
    )
    styles = _styles()
    width = document.width

    def section(title: str, header, body, fractions, empty_message: str) -> list:
        parts: list = [Paragraph(title, styles["heading"])]
        if body:
            parts.append(_table(header, body, [width * f for f in fractions], styles))
        else:
            parts.append(Paragraph(empty_message, styles["empty"]))
        return parts

    meta = (f"Generated {_when(report, report.generated_at)} &nbsp;|&nbsp; Date range: {date_range_label(report)}"
            f" &nbsp;|&nbsp; Service: {escape(report.service_name or 'All services')}")
    story: list = [Paragraph("QueueSmart report", styles["title"]), Paragraph(meta, styles["meta"]), Spacer(1, 6)]

    summary = _summary_rows(report)
    # Two metric/value pairs per row keeps the summary compact.
    half = (len(summary) + 1) // 2
    pairs = [list(summary[i]) + (list(summary[i + half]) if i + half < len(summary) else ["", ""])
             for i in range(half)]
    story += section("Summary", ("Metric", "Value", "Metric", "Value"), pairs, [0.3, 0.2, 0.3, 0.2], "")

    story += section("Services", _SERVICE_HEADER, [
        [s.name, _service_status(s), (s.priority or "").title(), s.expected_duration_minutes, s.waiting_now,
         s.visits, s.served, s.left, _minutes(s.average_wait_minutes), _minutes(s.longest_wait_minutes)]
        for s in report.services
    ], [0.2, 0.09, 0.08, 0.09, 0.09, 0.07, 0.07, 0.07, 0.11, 0.13], "No services match these filters.")

    story += section("Patients", _PATIENT_HEADER, [
        [p.name, p.email, p.visits, p.served, p.left, _minutes(p.average_wait_minutes),
         _when(report, p.first_visit_at), _when(report, p.last_visit_at), ", ".join(p.services)]
        for p in report.patients
    ], [0.13, 0.23, 0.06, 0.06, 0.05, 0.09, 0.11, 0.11, 0.16], "No patient visits in this range.")

    story += section("Visits", _VISIT_HEADER, [
        [v.ticket, v.patient_name, v.email, v.service_name, _when(report, v.joined_at),
         _when(report, v.finished_at), v.outcome.title(), v.waited_minutes]
        for v in report.visits
    ], [0.08, 0.15, 0.2, 0.14, 0.13, 0.13, 0.08, 0.09], "No visits in this range.")

    document.build(story, onFirstPage=_page_number, onLaterPages=_page_number)
    return buffer.getvalue()
