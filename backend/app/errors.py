"""Turns FastAPI's request validation errors into one simple shape:

    422 {"detail": "Please fix the highlighted fields.", "errors": {"email": "Email is required."}}

so the frontend can show each message next to its field.
"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

_MESSAGES = {
    "missing": "This field is required.",
    "string_type": "Must be text.",
    "string_too_long": "This value is too long.",
    "extra_forbidden": "Unknown field.",
    "model_attributes_type": "Request body must be a JSON object.",
    "json_invalid": "Request body is not valid JSON.",
}


def _field_name(error: dict) -> str:
    # ("body", "email") -> "email"; errors about the body itself -> "body".
    # Invalid JSON is located by character offset, not by field.
    if error["type"] == "json_invalid":
        return "body"
    parts = [str(part) for part in error["loc"] if part != "body"]
    return ".".join(parts) or "body"


def _message(error: dict) -> str:
    if error["type"] == "value_error":
        # Our validators raise ValueError("..."); pydantic prefixes "Value error, ".
        return str(error["ctx"]["error"])
    return _MESSAGES.get(error["type"], error["msg"])


async def validation_error_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    errors: dict[str, str] = {}
    for error in exc.errors():
        errors.setdefault(_field_name(error), _message(error))
    return JSONResponse(status_code=422, content={"detail": "Please fix the highlighted fields.", "errors": errors})


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(RequestValidationError, validation_error_handler)
