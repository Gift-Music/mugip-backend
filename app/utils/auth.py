from __future__ import annotations

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
from sqlalchemy.orm import Session
from sqlalchemy.sql import expression as sql_exp

import app.models.postgres as m
from app.constants import TZ_UTC
from app.settings import AppSettings
from app.utils import fastapi as fastapi_util
from app.utils.fastapi import get_app_settings, get_db_session

from .base_ import AppUtilBase

_PBKDF2_HASH_NAME = 'SHA256'
_PBKDF2_ITERATIONS = 100_000

_USER_LOGIN_TTL = 24  # 12 hours
_USER_REFRESH_TTL = 24 * 7  # 7 days

_VERIFY_TOKEN_LENGTH = 6
_VERIFY_TOKEN_VERIFICATION_TTL = 10 * 60  # 10 minutes


@dataclasses.dataclass
class AuthUtilError(Exception):
    code: str
    message: str
    detail: dict[str, Any] | None = None


def generate_random_token(length: int) -> str:
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))


def generate_hashed_password(password: str) -> str:
    pbkdf2_salt = os.urandom(16)
    pw_hash = hashlib.pbkdf2_hmac(
        _PBKDF2_HASH_NAME,
        password.encode('utf-8'),
        pbkdf2_salt,
        _PBKDF2_ITERATIONS,
    )

    return '%s:%s' % (
        binascii.hexlify(pbkdf2_salt).decode('utf-8'),
        binascii.hexlify(pw_hash).decode('utf-8'),
    )


def validate_hashed_password(password: str, hashed_password: str) -> bool:
    pbkdf2_salt_hex, pw_hash_hex = hashed_password.split(':')

    pw_challenge = hashlib.pbkdf2_hmac(
        _PBKDF2_HASH_NAME,
        password.encode('utf-8'),
        binascii.unhexlify(pbkdf2_salt_hex),
        _PBKDF2_ITERATIONS,
    )

    return pw_challenge == binascii.unhexlify(pw_hash_hex)


class AuthAppUtil(AppUtilBase):
    @property
    def redis_keyspace(self) -> str:
        return self.app_settings.REDIS_KEY_PREFIX + 'auth:'

    def generate_token(self, user_id: int) -> tuple[str, str]:
        access_token = jwt.encode(
            payload={
                'user_id': user_id,
                'iss': 'mugip',
                'exp': (
                    datetime.datetime.now(TZ_UTC) + datetime.timedelta(hours=_USER_LOGIN_TTL)
                ).timestamp(),
            },
            key=self.app_settings.SECRET_KEY,
            algorithm='HS256',
        )

        refresh_token = jwt.encode(
            payload={
                'user_id': user_id,
                'iss': 'mugip',
                'exp': (
                    datetime.datetime.now(TZ_UTC) + datetime.timedelta(hours=_USER_REFRESH_TTL)
                ).timestamp(),
            },
            key=self.app_settings.SECRET_KEY,
            algorithm='HS256',
        )

        # Redis 에 생성된 token 추가
        self.app_context.redis.set(f'{self.redis_keyspace}{user_id}', access_token)
        return access_token, refresh_token

    def issue_verify_token(self, email: str) -> str:
        token = generate_random_token(_VERIFY_TOKEN_LENGTH)
        self.app_context.redis.set(
            f'{self.redis_keyspace}verify:{token}',
            email,
            ex=_VERIFY_TOKEN_VERIFICATION_TTL,
        )
        return token

    def get_verify_token(self, token: str) -> str | None:
        email_bytes: bytes | None = self.app_context.redis.get(f'{self.redis_keyspace}verify:{token}')
        return email_bytes.decode() if email_bytes is not None else None

    def delete_verify_token(self, token: str) -> None:
        self.app_context.redis.delete(f'{self.redis_keyspace}verify:{token}')


user_auth_scheme = OAuth2PasswordBearer(
    tokenUrl='auth/login/oauth',
)


class _AuthFailedError(Exception):
    def __init__(self, code: str) -> None:
        self.code = code


async def user_auth_required(
    token: str = Depends(user_auth_scheme),
    app_settings: AppSettings = Depends(get_app_settings),
    db_session: Session = Depends(get_db_session),
) -> int:
    try:
        try:
            token_info = jwt.decode(
                jwt=token,
                key=app_settings.SECRET_KEY,
                algorithms=['HS256']
            )
        except jwt.ExpiredSignatureError:
            raise _AuthFailedError('token_is_expired')
        except jwt.DecodeError:
            raise _AuthFailedError('token_decode_failure')

        user_id = token_info.get('user_id')
        if not isinstance(user_id, int):
            raise _AuthFailedError('invalid_token_structure')

        is_user_exist: bool = db_session.scalar(
            sql_exp
            .exists()
            .where(m.UserModel.id == user_id)
            .select()
        )
        if not is_user_exist:
            raise _AuthFailedError('user_deleted')

    except _AuthFailedError as err:
        raise fastapi_util.AuthError(err.code, 'you have no permission')
    except Exception:
        raise fastapi_util.AuthError('unknown', 'you have no permission')

    return user_id
