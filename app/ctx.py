from __future__ import annotations

import contextlib
import logging
import uuid
from contextvars import ContextVar
from typing import TYPE_CHECKING, AsyncIterator, NamedTuple

import boto3
from mypy_boto3_s3 import S3Client
from redis.asyncio import ConnectionPool as RedisConnectionPool
from redis.asyncio import Redis

if TYPE_CHECKING:
    from .settings import AppSettings
    from .utils.rdb import RdbConn


logger = logging.getLogger(__name__)


_current_app_ctx: ContextVar[AppCtx] = ContextVar("_current_app_ctx")


class _current_app_ctx_getter:
    def __get__(self, obj, objtype=None):  # type: ignore
        return _current_app_ctx.get()


class AppCtx(NamedTuple):
    if TYPE_CHECKING:  # type: ignore
        current: AppCtx

    settings: AppSettings
    db: RdbConn
    redis: Redis
    s3: S3Client

    id: str | None = None


async def create_app_ctx(app_settings: AppSettings) -> AppCtx:
    from .utils.rdb import RdbConn

    socket_keepalive_options = {
        int(k): v
        for k, v in app_settings.REDIS_CONNECT_CONFIG.pop(
            "socket_keepalive_options", {}
        ).items()
    }

    return AppCtx(
        settings=app_settings,
        db=RdbConn(app_settings.DATABASE_URI),
        redis=Redis(
            connection_pool=RedisConnectionPool.from_url(
                app_settings.REDIS_CONNECT_URI,
                socket_keepalive_options=socket_keepalive_options,
                **app_settings.REDIS_CONNECT_CONFIG,
            )
        ),
        s3=boto3.client(
            service_name="s3",
            region_name="ap-northeast-2",
            aws_access_key_id=app_settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=app_settings.AWS_SECRET_ACCESS_KEY,
        ),
    )


@contextlib.asynccontextmanager
async def bind_app_ctx(app_ctx: AppCtx) -> AsyncIterator[None]:
    ctx_token = _current_app_ctx.set(app_ctx._replace(id=str(uuid.uuid4())))
    try:
        yield
    finally:
        try:
            await app_ctx.db.clear_scoped_session()
        except Exception:
            logger.warning("Failed to clear scoped session", exc_info=True)

        _current_app_ctx.reset(ctx_token)


AppCtx.current = _current_app_ctx_getter()  # type: ignore
