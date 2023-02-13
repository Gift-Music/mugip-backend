import pytest_asyncio
import pytest
from tests.helper import with_app_ctx, ensure_fresh_env
from app.settings import AppSettings
from httpx import AsyncClient
from tests.mock.user import create_user


class TestMusic:
    @pytest_asyncio.fixture(scope="class", autouse=True)
    async def _init_env(
        self, app_settings: AppSettings, app_client: AsyncClient
    ) -> None:
        async with with_app_ctx(app_settings):
            await ensure_fresh_env()
            await create_user(app_client)

    @pytest.mark.skip(reason="test it later")
    async def test_music_track_search_api(
        self,
        app_client: AsyncClient,
        user_access_token: str,
    ) -> None:
        await app_client.post(
            "/music/track",
            json={"q": "RE"},
            headers={"Authorization": "Bearer " + user_access_token},
        )
