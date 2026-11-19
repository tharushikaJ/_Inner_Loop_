import json
import re
import secrets
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import settings
from ..models.user import User
from ..schemas.auth_schema import LoginRequest, RegisterRequest
from ..utils.security import decode_microsoft_id_token, hash_password, verify_password


INVALID_CREDENTIALS = "Invalid email or password."
MANAGEMENT_MICROSOFT_SIGN_IN_REQUIRED = "Management accounts must sign in with Microsoft."


def get_microsoft_profile(access_token: str) -> dict:
    """Return only the Microsoft Graph fields used by the sign-in flow."""
    query = urlencode({"$select": "id,displayName,mail,userPrincipalName,jobTitle"})
    request = Request(
        f"https://graph.microsoft.com/v1.0/me?{query}",
        headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
    )
    try:
        with urlopen(request, timeout=10) as response:
            profile = json.load(response)
    except (HTTPError, URLError, OSError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to retrieve your Microsoft profile. Please try again.",
        ) from exc

    if not isinstance(profile, dict):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unable to verify your Microsoft profile.",
        )
    return profile


def role_for_microsoft_job_title(job_title: object) -> str:
    normalized_title = str(job_title or "").casefold()
    management_title = (
        "deputy general" in normalized_title
        or "general manager" in normalized_title
        or re.search(r"\bchief\b", normalized_title) is not None
    )
    return "management" if management_title else "employee"


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
    if user is not None and user.role == "management":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=MANAGEMENT_MICROSOFT_SIGN_IN_REQUIRED,
        )
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


def authenticate_microsoft_user(db: Session, id_token: str, access_token: str) -> User:
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

    profile = get_microsoft_profile(access_token)
    profile_email = str(profile.get("mail") or profile.get("userPrincipalName") or "").strip().lower()
    claim_object_id = str(claims.get("oid") or "").strip()
    profile_object_id = str(profile.get("id") or "").strip()
    profile_matches_identity = (
        bool(claim_object_id and profile_object_id and claim_object_id == profile_object_id)
        or profile_email == email
    )
    if not profile_matches_identity:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Microsoft profile does not match the authenticated account.",
        )

    job_title = str(profile.get("jobTitle") or "").strip()
    detected_role = role_for_microsoft_job_title(job_title)

    user = db.query(User).filter(func.lower(User.email) == email).first()
    if not user:
        display_name = str(
            profile.get("displayName")
            or claims.get("name")
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
            role=detected_role,
            designation=job_title or None,
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

    # An intern's role is managed separately and must never be replaced by
    # Microsoft profile data. Preserve the existing Microsoft sign-in policy:
    # intern accounts continue to use their existing authentication flow.
    if user.role == "intern":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Intern accounts cannot sign in through organization sign-in.",
        )

    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your InnerLoop account has been deactivated. Please contact an administrator.",
        )

    # Employee and management accounts are refreshed from the current Graph
    # job title on every Microsoft sign-in.
    user.role = detected_role
    user.designation = job_title or None
    db.commit()
    db.refresh(user)

    return user


def get_active_user(db: Session, user_id: int) -> User:
    user = db.query(User).filter(User.id == user_id, User.status == "active").first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )
    return user
