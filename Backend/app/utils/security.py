import logging

from datetime import datetime, timedelta, timezone
import json
from functools import lru_cache
from urllib.request import urlopen

import bcrypt
from jose import JWTError, jwk, jwt
from jose.exceptions import JOSEError

from ..config import settings

logger = logging.getLogger(__name__)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (TypeError, ValueError):
        return False


def create_access_token(user_id: int) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {"sub": str(user_id), "type": "access", "exp": expires_at}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> int | None:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        if payload.get("type") != "access":
            return None
        return int(payload.get("sub"))
    except (JWTError, TypeError, ValueError):
        return None


@lru_cache(maxsize=1)
def _microsoft_signing_keys() -> dict:
    url = f"https://login.microsoftonline.com/{settings.microsoft_tenant_id}/discovery/v2.0/keys"
    with urlopen(url, timeout=10) as response:
        return {key["kid"]: key for key in json.load(response)["keys"]}


def decode_microsoft_id_token(token: str) -> dict | None:
    if not settings.microsoft_tenant_id or not settings.microsoft_client_id:
        logger.error("Microsoft tenant ID or client ID is not configured.")
        return None
    try:
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        alg = header.get("alg") or "RS256"

        keys = _microsoft_signing_keys()
        key_data = keys.get(kid)
        if not key_data:
            _microsoft_signing_keys.cache_clear()
            keys = _microsoft_signing_keys()
            key_data = keys.get(kid)

        if not key_data or alg != "RS256":
            logger.warning("No matching signing key found for kid=%s or alg=%s", kid, alg)
            return None

        # Microsoft keys omit 'alg', which causes python-jose's jwk.construct to raise
        # JWKError('Unable to find an algorithm for key'). Explicitly providing alg fixes this.
        constructed_key = jwk.construct(key_data, algorithm=alg)
        issuers = [
            f"https://login.microsoftonline.com/{settings.microsoft_tenant_id}/v2.0",
            f"https://sts.windows.net/{settings.microsoft_tenant_id}/",
        ]
        claims = jwt.decode(
            token,
            constructed_key,
            algorithms=[alg],
            audience=settings.microsoft_client_id,
            issuer=issuers,
        )
        if claims.get("tid") != settings.microsoft_tenant_id:
            logger.warning("Token tenant ID %s does not match expected %s", claims.get("tid"), settings.microsoft_tenant_id)
            return None
        return claims
    except (JOSEError, OSError, ValueError, KeyError, TypeError) as exc:
        logger.exception("Failed to decode Microsoft ID token: %s", exc)
        _microsoft_signing_keys.cache_clear()
        return None
