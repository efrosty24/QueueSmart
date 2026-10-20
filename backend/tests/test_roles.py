import pytest

from app.auth.roles import Role, role_for_email


@pytest.mark.parametrize(
    "email",
    ["admin@university.edu", "clinic.admin@university.edu", "superadmin42@uni.edu", "ADMIN@university.edu"],
)
def test_admin_in_name_part_is_admin(email):
    assert role_for_email(email) is Role.ADMIN


@pytest.mark.parametrize("email", ["student@university.edu", "jane@admin.edu", "adm1n@university.edu"])
def test_everyone_else_is_patient(email):
    assert role_for_email(email) is Role.PATIENT
