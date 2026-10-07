from datetime import timedelta

import jwt
from django.conf import settings
from django.utils import timezone

ACCESS_TOKEN_EXPIRATION = timedelta(minutes=15000)
REFRESH_TOKEN_EXPIRATION = timedelta(days=30)
ALGORITHM = "HS256"


def create_token(user, token_type, lifetime):
    now = timezone.now()

    payload = {
        "sub": str(user.id),
        "token_type": token_type,
        "ver": user.token_version,
        "iat": now,
        "exp": now + lifetime,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def create_access_token(user):
    return create_token(user, "access", ACCESS_TOKEN_EXPIRATION)


def create_refresh_token(user):
    return create_token(user, "refresh", REFRESH_TOKEN_EXPIRATION)


def decode(token):
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"require": ["sub", "exp", "iat"]},
        )
    except jwt.PyJWTError:
        return None