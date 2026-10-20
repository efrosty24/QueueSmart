"""Request and response bodies for the auth endpoints.

StrictStr rejects non-string values (numbers, lists, null) instead of coercing
them. The outer max_length caps oversized input before the regex rules run;
the precise limits live in validation.py.
"""

from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StrictStr

from .roles import Role
from .validation import validate_email, validate_login_password, validate_new_password

Email = Annotated[StrictStr, Field(max_length=320), AfterValidator(validate_email)]


class _Request(BaseModel):
    # Unknown fields are an error, so a client can't slip in {"role": "admin"}.
    model_config = ConfigDict(extra="forbid")


class RegisterRequest(_Request):
    email: Email
    password: Annotated[StrictStr, Field(max_length=256), AfterValidator(validate_new_password)]


class LoginRequest(_Request):
    email: Email
    password: Annotated[StrictStr, Field(max_length=256), AfterValidator(validate_login_password)]


class UserOut(BaseModel):
    id: str
    email: str
    role: Role


class AuthResponse(BaseModel):
    """Returned by login and register. Send `token` as "Authorization: Bearer <token>"."""

    token: str
    expires_at: datetime
    user: UserOut
