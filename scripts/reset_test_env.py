import asyncio
from urllib.parse import urlparse

from asgi_lifespan import LifespanManager

from app import create_app
from app.context import AppContext
from app.settings import AppSettings


async def main() -> None:
    app_settings = AppSettings()
    test_app_settings = AppSettings(_env_file='.env.test')  # type: ignore
    target_app_settings = test_app_settings.copy()

    # we need to change the database name because we cannot connect if it does not exist
    test_db_name = urlparse(test_app_settings.DATABASE_URI).path.lstrip('/')
    target_app_settings.DATABASE_URI = app_settings.DATABASE_URI

    app = create_app(target_app_settings)

    async with LifespanManager(app):
        app_context = AppContext.from_app(app)

        # reset PostgreSQL
        db_conn = app_context.db_engine.connect()
        db_conn.execute(  # nosec
            f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '{test_db_name}'"
        )
        db_conn.execution_options(isolation_level='AUTOCOMMIT').execute(f'DROP DATABASE IF EXISTS "{test_db_name}"')
        db_conn.execution_options(isolation_level='AUTOCOMMIT').execute(f'CREATE DATABASE "{test_db_name}"')

        # reset Redis
        app_context.redis.flushdb()

asyncio.run(main())
