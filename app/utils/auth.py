from __future__ import annotations

import datetime
import random
import string

import jwt
import msgpack
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from redis import Redis

from app.config_proxy import config
from app.constants import TZ_UTC
from app.utils import server as server_utils
from app.utils.misc import lazystr

_USER_LOGIN_TTL = 30  # 30 minutes
_USER_TOKEN_REFESH_TTL = 2  # 2 days

_USER_SESSION_KEY_PREFIX = lazystr(lambda: config.REDIS_KEY_PREFIX + 'session:')


def _make_random_string(length: int) -> str:
    letters = string.ascii_letters + string.digits
    return ''.join((random.SystemRandom().choice(letters) for i in range(length)))


class AuthResult(BaseModel):
    user_id: int


user_auth_scheme = OAuth2PasswordBearer(tokenUrl='auth/login/fastapi')


class _AuthFailedError(Exception):
    def __init__(self, code: str) -> None:
        self.code = code


def user_auth_required(
    token: str = Depends(user_auth_scheme),
) -> AuthResult:
    try:
        try:
            token_info = jwt.decode(
                jwt=token,
                key=config.SECRET_KEY,
                algorithms=['HS256'],
            )
        except jwt.ExpiredSignatureError:
            raise _AuthFailedError('token_is_expired')
        except jwt.DecodeError:
            raise _AuthFailedError('token_decode_failure')

        user_id = token_info.get('user_id')

        if not isinstance(user_id, int):
            raise _AuthFailedError('invalid_token_structure')

    except _AuthFailedError as err:
        raise server_utils.AuthError(err.code, 'you have no permission')
    except Exception:
        raise server_utils.AuthError('unknown', 'you have no permission')

    return AuthResult(user_id=user_id)


def generate_tokens(user_id: int) -> tuple[str, str]:
    access_token = jwt.encode(
        payload={
            'user_id': user_id,
            'iss': config.HOST_NAME,
            'exp': (datetime.datetime.now(TZ_UTC) + datetime.timedelta(hours=_USER_LOGIN_TTL)).timestamp(),
        },
        key=config.SECRET_KEY,
        algorithm='HS256',
    )

    refresh_token = jwt.encode(
        payload={
            'user_id': user_id,
            'iss': config.HOST_NAME,
            'exp': (datetime.datetime.now(TZ_UTC) + datetime.timedelta(days=_USER_TOKEN_REFESH_TTL)).timestamp(),
        },
        key=config.SECRET_KEY,
        algorithm='HS256',
    )

    return access_token, refresh_token


def login_user(user_id: int, redis: Redis) -> None:
    token_nonce = _make_random_string(10)
    redis.set(
        _USER_SESSION_KEY_PREFIX + f'user_id:{user_id}:nonce:{token_nonce}',
        msgpack.dumps((user_id, None)),
        ex=_USER_LOGIN_TTL,
    )
