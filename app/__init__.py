from __future__ import annotations

import functools
import logging

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from setuptools_scm import get_version
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.log_helper import init_logger as _init_logger

from .controllers import ALL_ROUTERS
from .ctx import AppCtx, bind_app_ctx, create_app_ctx
from .settings import AppSettings
from .utils.fastapi import FASTAPI_RESPONSES, ErrorReportMiddleware

__version__ = get_version(root="..", relative_to=__file__)

logger = logging.getLogger(__name__)


def init_logger(app_settings: AppSettings) -> None:
    _init_logger(f"mugip-backend@{__version__}", app_settings)


def create_app(app_settings: AppSettings) -> FastAPI:
    app = FastAPI(responses=FASTAPI_RESPONSES)

    app.add_event_handler(
        "startup", functools.partial(_web_app_startup, app, app_settings)
    )
    app.add_event_handler("shutdown", functools.partial(_web_app_shutdown, app))

    for api_router in ALL_ROUTERS:
        app.include_router(api_router)

    return app


async def _web_app_startup(app: FastAPI, app_settings: AppSettings) -> None:
    app_ctx = await create_app_ctx(app_settings)

    app.extra["_app_ctx"] = app_ctx

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

    app.add_middleware(ErrorReportMiddleware)

    async def _ctx_middleware(
        request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        async with bind_app_ctx(app_ctx):
            response = await call_next(request)
        return response

    app.add_middleware(BaseHTTPMiddleware, dispatch=_ctx_middleware)


async def _web_app_shutdown(app: FastAPI) -> None:
    app_ctx: AppCtx = app.extra["_app_ctx"]

    try:
        await app_ctx.db.engine.dispose()
    except Exception:
        logger.warning("Failed dispose DB engine", exc_info=True)
