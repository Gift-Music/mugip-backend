import logging
from typing import TYPE_CHECKING

import fastapi
from elasticsearch import AsyncElasticsearch
from fastapi.middleware.cors import CORSMiddleware
from redis import BlockingConnectionPool as RedisBlockingConnectionPool
from redis import Redis
from sqlalchemy import create_engine

from .config_proxy import config
from .controllers import SUBAPP_LIST
from .controllers.index_ import router as index__router
from .log_helper import init_logger

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine

__all__ = ['init_environment', 'Server']

logger = logging.getLogger(__name__)


def init_environment() -> None:
    init_logger(__name__)

    if config.DEBUG_ALLOW_CORS_ALL_ORIGIN:
        logger.error('`DEBUG_ALLOW_CORS_ALL_ORIGIN` is on!')

    if config.DEBUG_ALLOW_NON_CERTIFICATED_USER_GET_TOKEN:
        logger.error('`DEBUG_ALLOW_NON_CERTIFICATED_USER_GET_TOKEN` is on!')


class Server:
    def __init__(self) -> None:
        self.web_app = fastapi.FastAPI(
            on_startup=[self._web_app_startup],
            on_shutdown=[self._web_app_shutdown],
        )

        if config.DEBUG_ALLOW_CORS_ALL_ORIGIN:
            self.web_app.add_middleware(
                CORSMiddleware,
                allow_origins=['*'],
                allow_credentials=True,
                allow_methods=['*'],
                allow_headers=['*'],
                expose_headers=['x-total'],
            )

        self.web_app.include_router(index__router)

        for mountpoint, subapp in SUBAPP_LIST:
            self.web_app.mount(mountpoint, subapp)

        self.db_engine: Engine | None = None

    def _web_app_startup(self) -> None:
        self.db_engine = create_engine(config.DATABASE_URI, **config.DATABASE_OPTIONS)

        self.redis = Redis(
            connection_pool=RedisBlockingConnectionPool.from_url(
                config.REDIS_CONNECT_URI,
                **config.REDIS_CONNECT_CONFIG
            )
        )

        self.es = AsyncElasticsearch(hosts=[config.ELASTICSEARCH_CONNECT_URI])

        for _, subapp in SUBAPP_LIST + [('/', self.web_app)]:
            if not isinstance(subapp, fastapi.FastAPI):
                continue

            subapp.extra['db_engine'] = self.db_engine
            subapp.extra['redis'] = self.redis
            subapp.extra['es'] = self.es

    def _web_app_shutdown(self) -> None:
        if self.db_engine is not None:
            self.db_engine.dispose()

        if self.redis is not None:
            self.redis.connection_pool.disconnect()

        if self.es is not None:
            self.es.close()
