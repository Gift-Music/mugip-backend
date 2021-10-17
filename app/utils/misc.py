from __future__ import annotations

import asyncio
import binascii
import datetime
import hashlib
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any, AsyncIterator, Callable, NamedTuple

from elasticsearch._async.client import AsyncElasticsearch
from fastapi import Request
from sqlalchemy.orm import Session
from sqlalchemy.sql import expression as sql_exp
from sqlalchemy.sql.expression import BooleanClauseList, ClauseElement

if TYPE_CHECKING:
    from redis import Redis
    from sqlalchemy.engine import Engine

from app.constants import TZ_UTC

_PBKDF2_HASH_NAME = 'SHA256'
_PBKDF2_ITERATIONS = 100_000

_SQLA_SESSION_CLOSER_THREADPOOL = ThreadPoolExecutor(1)


class lazystr:
    def __init__(self, func: Callable[[], str]) -> None:
        self._func = func

    def __str__(self) -> str:
        return self._func()

    def __add__(self, other: str) -> str:
        return self._func() + other

    def __mod__(self, other: str) -> str:
        return self._func() % other


class FilterExpr(NamedTuple):
    schema: dict[str, Any]
    to_query: Callable[[dict[str, Any], dict[str, Callable[[Any], BooleanClauseList]]], ClauseElement]
    description: str


def ts_to_dt(ts: int) -> datetime.datetime:
    return datetime.datetime.fromtimestamp(ts / 1000, tz=TZ_UTC)


def dt_to_ts(dt: datetime.datetime) -> int:
    return int(dt.timestamp() * 1000)


async def get_db_session(request: Request) -> AsyncIterator[Session]:
    # NOTE : This function is called by `fastapi.Depends` and it is not
    #        guaranteed to be in the same thread to the routing function.
    #        Therefore, we do not use scoped_session with ThreadLocal.
    db_engine: Engine = request.app.extra['db_engine']

    loop = asyncio.get_event_loop()

    session = Session(db_engine)

    try:
        yield session
    finally:
        await loop.run_in_executor(
            _SQLA_SESSION_CLOSER_THREADPOOL,
            session.close,
        )


def get_redis(request: Request) -> Redis:
    return request.app.extra['redis']  # type: ignore


def get_es(request: Request) -> AsyncElasticsearch:
    return request.app.extra['es']  # type: ignore


def get_client_ip(request: Request) -> str:
    x_forwarded_for = request.headers.get('X-FORWARDED-FOR')
    return (  # type: ignore
        (x_forwarded_for.split(',')[0]).split(':')[0]
        if x_forwarded_for
        else request.client.host
    )


def _filter_expr_to_query(
    filter_expr: dict[str, Any],
    key_func_dict: dict[str, Callable[[Any], BooleanClauseList]]
) -> ClauseElement:
    expr_list = []
    for key, value_or_exprs in filter_expr.items():
        if key == '$and':
            assert isinstance(value_or_exprs, list)
            expr_list.append(
                sql_exp.and_(
                    *[_filter_expr_to_query(expr, key_func_dict) for expr in value_or_exprs if expr]
                )
            )
        elif key == '$or':
            assert isinstance(value_or_exprs, list)
            expr_list.append(
                sql_exp.or_(
                    *[_filter_expr_to_query(expr, key_func_dict) for expr in value_or_exprs if expr]
                )
            )
        elif key == '$not':
            assert isinstance(value_or_exprs, dict)
            expr_list.append(
                sql_exp.not_(
                    _filter_expr_to_query(value_or_exprs, key_func_dict)
                )
            )
        elif key in key_func_dict:
            expr_list.append(
                key_func_dict[key](value_or_exprs)
            )
        else:
            raise RuntimeError('Func for the key is not defined', key)

    if not expr_list:
        return sql_exp.true()

    return sql_exp.and_(*expr_list)


def _filter_expr_to_schema(filter_key_to_schema: dict[str, dict[str, Any]]) -> dict[str, Any]:
    random_scheme_id = uuid.uuid4().hex

    return {
        '$id': random_scheme_id,
        'type': 'object',
        'properties': {
            '$and': {
                'type': 'array',
                'items': {'$ref': random_scheme_id},
            },
            '$or': {
                'type': 'array',
                'items': {'$ref': random_scheme_id},
            },
            '$not': {'$ref': random_scheme_id},
            **filter_key_to_schema
        },
        'additionalProperties': False,
    }


def build_filter_expr(filter_key_to_schema: dict[str, dict[str, Any]]) -> FilterExpr:
    return FilterExpr(
        schema=_filter_expr_to_schema(filter_key_to_schema),
        to_query=_filter_expr_to_query,
        description='filtering on %s' % ', '.join(
            f'`{key}:{expr.get("type", "any")}`'
            for key, expr in filter_key_to_schema.items()
        )
    )


def generate_hashed_password(password: str) -> str:
    pbkdf2_salt = os.urandom(16)
    pw_hash = hashlib.pbkdf2_hmac(
        _PBKDF2_HASH_NAME,
        password.encode('utf-8'),
        pbkdf2_salt,
        _PBKDF2_ITERATIONS
    )

    return '%s:%s' % (
        binascii.hexlify(pbkdf2_salt).decode('utf-8'),
        binascii.hexlify(pw_hash).decode('utf-8')
    )


def validate_hashed_password(password: str, hashed_password: str) -> bool:
    pbkdf2_salt_hex, pw_hash_hex = hashed_password.split(':')

    pw_challenge = hashlib.pbkdf2_hmac(
        _PBKDF2_HASH_NAME,
        password.encode('utf-8'),
        binascii.unhexlify(pbkdf2_salt_hex),
        _PBKDF2_ITERATIONS
    )

    return pw_challenge == binascii.unhexlify(pw_hash_hex)
