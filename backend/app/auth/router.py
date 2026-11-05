from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from .dependencies import CurrentUser, get_current_user, get_token
from .passwords import DUMMY_HASH, verify_password
from .schemas import AuthResponse, LoginRequest, ProfileDetails, ProfileOut, RegisterRequest, UserOut
from .sessions import sessions
from .store import EmailTakenError, User, users

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _to_out(user: User) -> UserOut:
    return UserOut(id=user.id, email=user.email, role=user.role)


def _start_session(user: User) -> AuthResponse:
    token, session = sessions.create(user.id)
    return AuthResponse(token=token, expires_at=session.expires_at, user=_to_out(user))


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest) -> AuthResponse:
    """Creates an account and signs it in right away."""
    try:
        user = users.create(body.email, body.password, body.full_name, body.contact_info, body.preferences)
    except EmailTakenError:
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists.") from None
    return _start_session(user)


@router.post("/login")
def login(body: LoginRequest) -> AuthResponse:
    user = users.get_by_email(body.email)
    # Always run bcrypt, even for unknown emails, so response time doesn't reveal which emails exist.
    password_ok = verify_password(body.password, user.password_hash if user else DUMMY_HASH)
    if not user or not password_ok:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password.")
    return _start_session(user)


@router.get("/me")
def me(user: CurrentUser) -> UserOut:
    """The signed-in user. The frontend uses this to confirm a saved session and its role."""
    return _to_out(user)


@router.get("/profile")
def profile(user: CurrentUser) -> ProfileOut:
    saved = users.get_profile(user.id)
    if saved is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Profile not found.")
    return ProfileOut(**asdict(saved))


@router.put("/profile")
def update_profile(body: ProfileDetails, user: CurrentUser) -> ProfileOut:
    saved = users.update_profile(user.id, body.full_name, body.contact_info, body.preferences)
    if saved is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Profile not found.")
    return ProfileOut(**asdict(saved))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(get_current_user)])
def logout(token: Annotated[str, Depends(get_token)]) -> Response:
    sessions.revoke(token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
