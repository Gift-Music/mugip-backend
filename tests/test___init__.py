from __future__ import annotations

from typing import TYPE_CHECKING
from tests.helper import with_app_ctx, ensure_fresh_env

import pytest
from httpx import AsyncClient

if TYPE_CHECKING:
    from app.settings import AppSettings


def test_init_logger(app_settings: AppSettings) -> None:
    from app import init_logger

    init_logger(app_settings)


@pytest.mark.asyncio
async def test_create_app(app_client: AsyncClient, app_settings: AppSettings) -> None:
    async with with_app_ctx(app_settings):
        await ensure_fresh_env()
    ping_r = await app_client.get("/_ping")
    assert ping_r.status_code == 200
    assert ping_r.json() == {"ok": True}
