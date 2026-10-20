from fastapi import APIRouter, HTTPException, status

from .passwords import DUMMY_HASH, verify_password
from .schemas import LoginRequest, RegisterRequest, UserOut
from .store import EmailTakenError, User, users

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _to_out(user: User) -> UserOut:
    return UserOut(id=user.id, email=user.email, role=user.role)


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest) -> UserOut:
    try:
        user = users.create(body.email, body.password)
    except EmailTakenError:
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists.") from None
    return _to_out(user)


@router.post("/login")
def login(body: LoginRequest) -> UserOut:
    user = users.get_by_email(body.email)
    # Always run bcrypt, even for unknown emails, so response time doesn't reveal which emails exist.
    password_ok = verify_password(body.password, user.password_hash if user else DUMMY_HASH)
    if not user or not password_ok:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password.")
    return _to_out(user)
