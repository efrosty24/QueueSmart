"""Role handling: patients (students, faculty, staff) vs clinic administrators."""

from enum import StrEnum


class Role(StrEnum):
    PATIENT = "patient"
    ADMIN = "admin"


def role_for_email(email: str) -> Role:
    """Mock rule until the university directory is wired up: an account is an
    administrator when the name part of its email (before the @) contains
    "admin", e.g. admin@university.edu or clinic.admin@university.edu.
    Only the name part counts, so jane@admin.edu stays a patient.
    """
    name = email.split("@", 1)[0]
    return Role.ADMIN if "admin" in name.lower() else Role.PATIENT
