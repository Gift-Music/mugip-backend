import pytest_asyncio
import pytest

from tests.helper import (
    with_app_ctx,
    ensure_fresh_env,
    create_async_function,
    FakeResponse,
)
from tests.mock.user import create_user
from httpx import AsyncClient
from _pytest.monkeypatch import MonkeyPatch

from app.settings import AppSettings
from app.utils import auth as auth_util
from app.utils import spotify as spotify_util
from app.utils import fastapi as fastapi_util
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
    async def spotify_access_token(
        self,
        app_settings: AppSettings,
    ) -> str:
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
            params={"q": "abcdefu"},
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
            "spotify_access_token": spotify_access_token,
        }
        resp = await app_client.get(
            "/music/track/4fouWK6XVHhzl78KzQ1UjL", headers=headers
        )

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
            "spotify_access_token": spotify_access_token,
        }
        resp = await app_client.get(
            "/music/artist/2VSHKHBTiXWplO8lxcnUC9", headers=headers
        )

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

    @pytest.mark.parametrize(
        "expected_error_code, expected_error_message",
        [("spotify_error", "spotify_error")],
    )
    async def test_music_track_search_api_fail(
        self,
        monkeypatch: MonkeyPatch,
        app_settings: AppSettings,
        expected_error_code: str | None,
        expected_error_message: str | None,
    ) -> None:
        async with with_app_ctx(app_settings):
            with monkeypatch.context() as mp:
                mp.setattr(
                    AsyncClient,
                    "get",
                    create_async_function(
                        lambda *args, **kwargs: FakeResponse(
                            data={"message": "something_error_happens_at_spotify"},
                            status_code=409,
                        )
                    ),
                )
                q = {"q": "abcdefu"}

                with pytest.raises(fastapi_util.LogicError) as err:
                    await fastapi_music.music_track_search_api(q=q)

        assert err.value.code == expected_error_code
        assert err.value.message == expected_error_message

    @pytest.mark.parametrize(
        "expected_error_code, expected_error_message",
        [("no_access_token", "you should send spotify access token")],
    )
    async def test_music_track_get_api_fail_no_token(
        self,
        app_client: AsyncClient,
        user_access_token: str,
        expected_error_code: str | None,
        expected_error_message: str | None,
    ) -> None:
        headers = {
            "Authorization": "Bearer " + user_access_token,
        }
        resp = await app_client.get(
            "/music/track/4fouWK6XVHhzl78KzQ1UjL", headers=headers
        )

        assert (resp.json() or {}).get("detail", {}).get("code") == expected_error_code
        assert (resp.json() or {}).get("detail", {}).get(
            "message"
        ) == expected_error_message

    @pytest.mark.parametrize(
        "expected_error_code, expected_error_message",
        [("spotify_error", "spotify_error")],
    )
    async def test_music_track_get_api_fail(
        self,
        app_client: AsyncClient,
        user_access_token: str,
        expected_error_code: str | None,
        expected_error_message: str | None,
    ) -> None:
        headers = {
            "Authorization": "Bearer " + user_access_token,
            "spotify_access_token": "wrong_spotify_token",
        }
        resp = await app_client.get(
            "/music/track/4fouWK6XVHhzl78KzQ1UjL", headers=headers
        )

        assert (resp.json() or {}).get("detail", {}).get("code") == expected_error_code
        assert (resp.json() or {}).get("detail", {}).get(
            "message"
        ) == expected_error_message

    @pytest.mark.parametrize(
        "expected_error_code, expected_error_message",
        [("no_access_token", "you should send spotify access token")],
    )
    async def test_music_artist_get_api_fail_no_token(
        self,
        app_client: AsyncClient,
        user_access_token: str,
        expected_error_code: str | None,
        expected_error_message: str | None,
    ) -> None:
        headers = {
            "Authorization": "Bearer " + user_access_token,
        }
        resp = await app_client.get(
            "/music/artist/2VSHKHBTiXWplO8lxcnUC9", headers=headers
        )

        assert (resp.json() or {}).get("detail", {}).get("code") == expected_error_code
        assert (resp.json() or {}).get("detail", {}).get(
            "message"
        ) == expected_error_message

    @pytest.mark.parametrize(
        "expected_error_code, expected_error_message",
        [("spotify_error", "spotify_error")],
    )
    async def test_music_artist_get_api_fail(
        self,
        app_client: AsyncClient,
        user_access_token: str,
        expected_error_code: str | None,
        expected_error_message: str | None,
    ) -> None:
        headers = {
            "Authorization": "Bearer " + user_access_token,
            "spotify_access_token": "wrong_spotify_token",
        }
        resp = await app_client.get(
            "/music/artist/2VSHKHBTiXWplO8lxcnUC9", headers=headers
        )

        assert (resp.json() or {}).get("detail", {}).get("code") == expected_error_code
        assert (resp.json() or {}).get("detail", {}).get(
            "message"
        ) == expected_error_message
