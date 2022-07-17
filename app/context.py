from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple

from fastapi import FastAPI
from redis import Redis
from sqlalchemy.engine import Engine

if TYPE_CHECKING:
    from .settings import AppSettings
    from .utils import AppUtils


class AppContext(NamedTuple):
    app_settings: AppSettings
    db_engine: Engine
    redis: Redis
    app_utils: AppUtils

    @staticmethod
    def from_app(app: FastAPI) -> AppContext:
        try:
            return app.extra["app_context"]  # type: ignore
        except KeyError:
            raise RuntimeError("App context is not initialized")
