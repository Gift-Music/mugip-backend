from asyncio import AbstractEventLoop
from typing import AsyncIterator, Iterator

import pytest
import pytest_asyncio
import uvloop
from asgi_lifespan import LifespanManager
from httpx import AsyncClient

from app import create_app
from app.settings import AppSettings


@pytest.fixture(scope="session")
def app_settings() -> AppSettings:
    return AppSettings(_env_file=".env.test")  # type: ignore


@pytest.fixture(scope="class")
def event_loop() -> Iterator[AbstractEventLoop]:
    loop = uvloop.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="class")
async def app_client(app_settings: AppSettings) -> AsyncIterator[AsyncClient]:
    app = create_app(app_settings)
    async with AsyncClient(
        app=app, base_url="http://test"
    ) as app_client, LifespanManager(app):
        yield app_client
