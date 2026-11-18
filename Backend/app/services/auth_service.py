import secrets

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import settings
from ..models.user import User
from ..schemas.auth_schema import LoginRequest, RegisterRequest
from ..utils.security import decode_microsoft_id_token, hash_password, verify_password


INVALID_CREDENTIALS = "Invalid email or password."


def register_user(db: Session, payload: RegisterRequest) -> User:
    existing_user = db.query(User).filter(User.email == payload.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    supervisor = None
    if payload.assigned_supervisor_id is not None:
        supervisor = db.query(User).filter(
            User.id == payload.assigned_supervisor_id,
            User.role == "employee",
            User.status == "active",
        ).first()
        if not supervisor:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The selected supervisor is not an active employee or does not exist.",
            )

    user = User(
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role,
        designation=payload.designation,
        department=payload.department,
        assigned_supervisor_id=supervisor.id if supervisor else None,
        status="active",
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        ) from None
    db.refresh(user)
    return user


def authenticate_user(db: Session, payload: LoginRequest) -> User:
    user = db.query(User).filter(User.email == payload.email).first()
    valid = (
        user is not None
        and user.status == "active"
        and verify_password(payload.password, user.password_hash)
    )
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=INVALID_CREDENTIALS,
        )
    return user


def authenticate_microsoft_user(db: Session, id_token: str) -> User:
    claims = decode_microsoft_id_token(id_token)
    email = str(
        (claims or {}).get("preferred_username")
        or (claims or {}).get("email")
        or (claims or {}).get("upn")
        or (claims or {}).get("unique_name")
        or ""
    ).strip().lower()

    if not claims or not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Use your SLT Microsoft account to sign in.",
        )

    email_domain = settings.microsoft_email_domain.strip().lower().lstrip("@")
    if email_domain and not email.endswith(f"@{email_domain}"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization Microsoft accounts can access InnerLoop.",
        )

    user = db.query(User).filter(func.lower(User.email) == email).first()
    if not user:
        display_name = str(
            claims.get("name")
            or " ".join(
                part for part in (claims.get("given_name"), claims.get("family_name")) if part
            )
            or email.split("@", 1)[0]
        ).strip()
        user = User(
            name=display_name,
            email=email,
            # Microsoft-only accounts do not use password authentication.
            password_hash=hash_password(secrets.token_urlsafe(32)),
            role="employee",
            status="active",
        )
        db.add(user)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            user = db.query(User).filter(func.lower(User.email) == email).first()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Unable to create your InnerLoop account. Please try again.",
                ) from None
        else:
            db.refresh(user)

    if user.role != "employee":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only employee accounts can access InnerLoop through organization sign-in.",
        )
    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your InnerLoop account has been deactivated. Please contact an administrator.",
        )
    return user


def get_active_user(db: Session, user_id: int) -> User:
    user = db.query(User).filter(User.id == user_id, User.status == "active").first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )
    return user
