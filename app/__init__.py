from __future__ import annotations

import asyncio
import functools
import logging
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis import BlockingConnectionPool as RedisBlockingConnectionPool
from redis import Redis
from setuptools_scm import get_version
from sqlalchemy import create_engine

from app.log_helper import init_logger as _init_logger

from .context import AppContext
from .controllers import ALL_ROUTERS
from .settings import AppSettings
from .utils import AppUtils
from .utils.fastapi import FASTAPI_RESPONSES, ErrorReportAndForgetMiddleware

__version__ = get_version(root="..", relative_to=__file__)

logger = logging.getLogger(__name__)


def init_logger(app_settings: AppSettings) -> None:
    _init_logger(f"mugip-backend@{__version__}", app_settings)


def create_app(app_settings: AppSettings) -> FastAPI:
    app = FastAPI(responses=FASTAPI_RESPONSES)
    app.add_event_handler(
        "startup",
        functools.partial(_web_app_startup, app=app, app_settings=app_settings),
    )
    app.add_event_handler("shutdown", functools.partial(_web_app_shutdown, app=app))

    if app_settings.DEBUG_ALLOW_CORS_ALL_ORIGIN:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=["x-total"],
        )
        logger.error("`DEBUG_ALLOW_CORS_ALL_ORIGIN` is on!")

    if app_settings.DEBUG_ALLOW_NON_CERTIFICATED_USER_GET_TOKEN:
        logger.error("`DEBUG_ALLOW_NON_CERTIFICATED_USER_GET_TOKEN` is on!")

    app.add_middleware(ErrorReportAndForgetMiddleware)

    for router in ALL_ROUTERS:
        app.include_router(router)

    return app


async def _web_app_startup(app: FastAPI, app_settings: AppSettings) -> None:
    if app_settings.THREAD_POOL_SIZE is not None:
        loop = asyncio.get_event_loop()
        # NOTE : this is only applicable for `starlette <= 0.14.2`
        loop.set_default_executor(ThreadPoolExecutor(app_settings.THREAD_POOL_SIZE))

    db_engine = create_engine(
        app_settings.DATABASE_URI,
        logging_name="sa_logger",
        **app_settings.DATABASE_OPTIONS,
    )

    # NOTE : prevent SQLA's own logs to be propagated to API logger
    logging.getLogger("api.orm.base.EngineWrapper.sa_logger").propagate = False

    socket_keepalive_options = {
        int(k): v
        for k, v in app_settings.REDIS_CONNECT_CONFIG.pop(
            "socket_keepalive_options", {}
        ).items()
    }

    redis = Redis(
        connection_pool=RedisBlockingConnectionPool.from_url(
            app_settings.REDIS_CONNECT_URI,
            socket_keepalive_options=socket_keepalive_options,
            **app_settings.REDIS_CONNECT_CONFIG,
        )
    )

    app_context = AppContext(
        app_settings=app_settings,
        db_engine=db_engine,
        redis=redis,
        app_utils=AppUtils(app),
    )

    app.extra["app_context"] = app_context


async def _web_app_shutdown(app: FastAPI) -> None:
    app_context = AppContext.from_app(app)

    app_context.db_engine.dispose()

    app_context.redis.connection_pool.disconnect()
