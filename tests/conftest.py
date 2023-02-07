from asyncio import AbstractEventLoop
from typing import AsyncIterator, Iterator

import pytest
import pytest_asyncio
import uvloop
from asgi_lifespan import LifespanManager
from httpx import AsyncClient

from app import create_app
from app.settings import AppSettings
from tests import constants as test_c


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


@pytest_asyncio.fixture(scope="class")
async def user_access_token(app_client: AsyncClient) -> str:
    resp = await app_client.post(
        "/auth/login",
        json={
            "email": test_c.DEFAULT_USER_EMAIL,
            "password": test_c.DEFAULT_USER_PASSWORD,
        },
    )

    return resp.json()["access_token"]  # type: ignore
