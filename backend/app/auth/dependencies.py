"""FastAPI dependencies for protecting routes."""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .sessions import sessions
from .store import User, users

# auto_error=False so a missing header gets our own 401 message instead of a 403.
_bearer = HTTPBearer(auto_error=False)


def _unauthorized() -> HTTPException:
    return HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        "Your session has expired or is invalid. Please sign in again.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_token(credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)]) -> str:
    if credentials is None:
        raise _unauthorized()
    return credentials.credentials


def get_current_user(token: Annotated[str, Depends(get_token)]) -> User:
    session = sessions.get(token)
    user = users.get_by_id(session.user_id) if session else None
    if user is None:
        raise _unauthorized()
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
