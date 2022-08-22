from __future__ import annotations

import asyncio
import binascii
import dataclasses
import datetime
import hashlib
import os
import random
import string
from typing import Any

import jwt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.sql import expression as sql_exp

import app.models.postgres as m
from app.constants import TZ_UTC
from app.ctx import AppCtx
from app.utils import fastapi as fastapi_util

_PBKDF2_HASH_NAME = "SHA256"
_PBKDF2_ITERATIONS = 100_000

_USER_LOGIN_TTL = 24  # 12 hours
_USER_REFRESH_TTL = 24 * 7  # 7 days


@dataclasses.dataclass
class AuthUtilError(Exception):
    code: str
    message: str
    detail: dict[str, Any] | None = None


def generate_random_token(length: int) -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))


async def generate_hashed_password(password: str) -> str:
    def _inner() -> str:
        pbkdf2_salt = os.urandom(16)
        pw_hash = hashlib.pbkdf2_hmac(
            _PBKDF2_HASH_NAME,
            password.encode(),
            pbkdf2_salt,
            _PBKDF2_ITERATIONS,
        )

        return "%s:%s" % (
            binascii.hexlify(pbkdf2_salt).decode(),
            binascii.hexlify(pw_hash).decode(),
        )

    return await asyncio.get_event_loop().run_in_executor(None, _inner)


async def validate_hashed_password(password: str, hashed_password: str) -> bool:
    def _inner() -> bool:
        pbkdf2_salt_hex, pw_hash_hex = hashed_password.split(":")

        pw_challenge = hashlib.pbkdf2_hmac(
            _PBKDF2_HASH_NAME,
            password.encode(),
            binascii.unhexlify(pbkdf2_salt_hex),
            _PBKDF2_ITERATIONS,
        )

        return pw_challenge == binascii.unhexlify(pw_hash_hex)

    return await asyncio.get_event_loop().run_in_executor(None, _inner)


def generate_token(user_id: int) -> tuple[str, str]:
    access_token = jwt.encode(
        payload={
            "user_id": user_id,
            "iss": "mugip",
            "exp": (
                datetime.datetime.now(TZ_UTC)
                + datetime.timedelta(hours=_USER_LOGIN_TTL)
            ).timestamp(),
        },
        key=AppCtx.settings.SECRET_KEY,
        algorithm="HS256",
    )

    refresh_token = jwt.encode(
        payload={
            "user_id": user_id,
            "iss": "mugip",
            "exp": (
                datetime.datetime.now(TZ_UTC)
                + datetime.timedelta(hours=_USER_REFRESH_TTL)
            ).timestamp(),
        },
        key=AppCtx.settings.SECRET_KEY,
        algorithm="HS256",
    )

    return access_token, refresh_token


user_auth_scheme = OAuth2PasswordBearer(
    tokenUrl="auth/login/oauth",
)


class _AuthFailedError(Exception):
    def __init__(self, code: str) -> None:
        self.code = code


async def user_auth_required(token: str = Depends(user_auth_scheme)) -> int:
    try:
        try:
            token_info = jwt.decode(
                jwt=token, key=AppCtx.settings.SECRET_KEY, algorithms=["HS256"]
            )
        except jwt.ExpiredSignatureError:
            raise _AuthFailedError("token_is_expired")
        except jwt.DecodeError:
            raise _AuthFailedError("token_decode_failure")

        user_id = token_info.get("user_id")
        if not isinstance(user_id, int):
            raise _AuthFailedError("invalid_token_structure")

        is_user_exist: bool = await AppCtx.current.db.session.scalar(
            sql_exp.exists().where(m.User.id == user_id).select()
        )
        if not is_user_exist:
            raise _AuthFailedError("user_deleted")

    except _AuthFailedError as err:
        raise fastapi_util.AuthError(err.code, "you have no permission")
    except Exception:
        raise fastapi_util.AuthError("unknown", "you have no permission")

    return user_id
