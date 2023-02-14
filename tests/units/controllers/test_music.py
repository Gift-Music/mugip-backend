import pytest_asyncio
import pytest
import httpx

from tests.helper import with_app_ctx, ensure_fresh_env
from tests.mock.user import create_user
from httpx import AsyncClient
from _pytest.monkeypatch import MonkeyPatch

from app.settings import AppSettings
from app.utils import auth as auth_util
from app.utils import spotify as spotify_util
from app.controllers import music as fastapi_music


class TestMusic:
    spfy_handler = spotify_util.SpotifyApiHandler() 

    @pytest_asyncio.fixture(scope="class", autouse=True)
    async def _init_env(
        self, app_settings: AppSettings, app_client: AsyncClient
    ) -> None:
        async with with_app_ctx(app_settings):
            await ensure_fresh_env()
            await create_user(app_client)

    @pytest_asyncio.fixture(scope="class")
    async def spotify_access_token(self, app_settings: AppSettings,) -> str:
        async with with_app_ctx(app_settings):
            spotify_access_token = await self.spfy_handler.client_credentials

            return spotify_access_token

    async def test_music_track_search_api(
        self,
        app_client: AsyncClient,
        user_access_token: str,
    ) -> None:
        resp = await app_client.get(
            "/music/track",
            params={"q": "별을 담은 시"},
            headers={"Authorization": "Bearer " + user_access_token},
        )

        assert resp.status_code == 200
        assert resp.json() is not None

    async def test_music_track_get_api(
        self,
        app_client: AsyncClient,
        user_access_token: str,
        spotify_access_token: str,
    ) -> None:
        headers = {
            "Authorization": "Bearer " + user_access_token,
            "spotify_access_token": spotify_access_token
        }
        resp = await app_client.get('/music/track/4fouWK6XVHhzl78KzQ1UjL', headers=headers)

        assert resp.status_code == 200
        assert resp.json() is not None

    async def test_music_artist_get_api(
        self,
        app_client: AsyncClient,
        user_access_token: str,
        spotify_access_token: str,
    ) -> None:
        headers = {
            "Authorization": "Bearer " + user_access_token,
            "spotify_access_token": spotify_access_token
        }
        resp = await app_client.get('/music/artist/2VSHKHBTiXWplO8lxcnUC9', headers=headers)

        assert resp.status_code == 200
        assert resp.json() is not None

class TestMusicFail:
    @pytest_asyncio.fixture(scope="class", autouse=True)
    async def _init_env(
        self, app_settings: AppSettings, app_client: AsyncClient
    ) -> None:
        async with with_app_ctx(app_settings):
            await ensure_fresh_env()
            await create_user(app_client)

    async def test_music_track_search_api_fail(
        self,
    ) -> None:
        pass

    async def test_music_track_get_api_fail_no_token(
        self,
    ) -> None:
        pass

    async def test_music_track_get_api_fail(
        self,
    ) -> None:
        pass

    async def test_music_artist_get_api_fail_no_token(
        self,
    ) -> None:
        pass

    async def test_music_artist_get_api_fail(
        self,
    ) -> None:
        pass
