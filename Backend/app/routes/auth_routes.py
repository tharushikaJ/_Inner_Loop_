from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models.user import User
from ..schemas.auth_schema import (
    AuthResponse,
    LoginRequest,
    MicrosoftLoginRequest,
    MessageResponse,
    RegisterRequest,
)
from ..schemas.user_schema import SupervisorOption, UserResponse
from ..services.auth_service import authenticate_microsoft_user, authenticate_user, register_user
from ..utils.permissions import get_current_user
from ..utils.security import create_access_token


router = APIRouter(prefix="/api/auth", tags=["authentication"])


@router.get("/supervisors", response_model=list[SupervisorOption])
def registration_supervisors(db: Session = Depends(get_db)):
    """Expose only active employee IDs and names needed during registration."""
    return db.query(User).filter(
        User.role == "employee", User.status == "active"
    ).order_by(User.name.asc()).all()


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    user = register_user(db, payload)
    return AuthResponse(message="Registration successful. You can now sign in.", user=user)


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = authenticate_user(db, payload)
    token = create_access_token(user.id)
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=token,
        max_age=settings.access_token_expire_minutes * 60,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path="/",
    )
    return AuthResponse(message="Login successful.", user=user)


@router.post("/microsoft", response_model=AuthResponse)
def microsoft_login(payload: MicrosoftLoginRequest, response: Response, db: Session = Depends(get_db)):
    user = authenticate_microsoft_user(db, payload.id_token)
    token = create_access_token(user.id)
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=token,
        max_age=settings.access_token_expire_minutes * 60,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path="/",
    )
    return AuthResponse(message="Microsoft sign-in successful.", user=user)


@router.get("/me", response_model=UserResponse)
def me(user=Depends(get_current_user)):
    return user


@router.post("/logout", response_model=MessageResponse)
def logout(response: Response):
    response.delete_cookie(
        key=settings.auth_cookie_name,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path="/",
    )
    return MessageResponse(message="Logout successful.")
