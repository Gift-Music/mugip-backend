import urllib.parse
import uuid
from asyncio import AbstractEventLoop
from typing import AsyncIterator, Iterator

import pytest
import uvloop
from asgi_lifespan import LifespanManager
from httpx import AsyncClient

import app.models.postgres as m
from app import create_app
from app.context import AppContext
from app.settings import AppSettings


@pytest.fixture(scope="session")
def event_loop() -> Iterator[AbstractEventLoop]:
    loop = uvloop.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def _app_settings() -> AppSettings:
    return AppSettings(_env_file=".env.test")  # type: ignore


@pytest.fixture(autouse=True, scope="session")
@pytest.mark.asyncio
async def _prepare_services(_app_settings: AppSettings) -> AsyncIterator[None]:
    app = create_app(_app_settings)

    async with LifespanManager(app):
        app_context = AppContext.from_app(app)
        try:
            if app_context.db_engine.execute(
                "SELECT EXISTS(SELECT 1 FROM pg_catalog.pg_tables WHERE schemaname = 'public')"
            ).scalar():
                raise RuntimeError("`PostgreSQL` service is not in the fresh state")

            if app_context.redis.scan() != (0, []):
                raise RuntimeError("`Redis` service is not in the fresh state")

        except Exception as ex:
            pytest.exit(msg=f"Failed to prepare services : {ex}", returncode=1)

        try:
            m.ModelBase.metadata.create_all(app_context.db_engine)
            # To prevent "source database is being accessed by other users" when copying database
            app_context.db_engine.dispose()
            yield
        finally:
            m.ModelBase.metadata.drop_all(app_context.db_engine)


@pytest.fixture(scope="class")
@pytest.mark.asyncio
async def app_client(_app_settings: AppSettings) -> AsyncIterator[AsyncClient]:
    target_app_settings = _app_settings.copy()

    # for performance, create a new temproal database by copying the test database
    test_db_name = urllib.parse.urlparse(_app_settings.DATABASE_URI).path.lstrip("/")
    temp_db_name = f"temp-{uuid.uuid4()}"
    target_app_settings.DATABASE_URI = urllib.parse.urlunparse(  # type: ignore
        urllib.parse.urlparse(_app_settings.DATABASE_URI)._replace(
            path=f"/{temp_db_name}"
        )
    )

    prepare_app = create_app(_app_settings)

    async with LifespanManager(prepare_app):
        prepare_app_context = AppContext.from_app(prepare_app)
        try:
            db_conn = prepare_app_context.db_engine.connect()
            db_conn.execution_options(isolation_level="AUTOCOMMIT").execute(
                f'CREATE DATABASE "{temp_db_name}" WITH TEMPLATE "{test_db_name}"'
            )

            app = create_app(target_app_settings)
            async with AsyncClient(
                app=app, base_url="http://test"
            ) as app_client, LifespanManager(app):
                yield app_client
        finally:
            db_conn.execute(  # nosec
                f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '{temp_db_name}'"
            )
            db_conn.execution_options(isolation_level="AUTOCOMMIT").execute(
                f'DROP DATABASE IF EXISTS "{temp_db_name}"'
            )


@pytest.fixture(scope="class")
@pytest.mark.asyncio
async def app_context(app_client: AsyncClient) -> AppContext:
    return AppContext.from_app(app_client._transport.app)  # type: ignore
