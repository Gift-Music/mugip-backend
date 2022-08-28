import pytest_asyncio
from tests.helper import with_app_ctx, ensure_fresh_env
from app.settings import AppSettings
from httpx import AsyncClient
from app.utils import oauth as oauth_util
from _pytest.monkeypatch import MonkeyPatch
from tests.helper import FakeResponse, create_async_function


class TestAuth:
    @pytest_asyncio.fixture(scope="class", autouse=True)
    async def _init_env(self, app_settings: AppSettings) -> None:
        async with with_app_ctx(app_settings):
            await ensure_fresh_env()

    async def test_get_social_token(
        self,
        monkeypatch: MonkeyPatch,
        app_settings: AppSettings,
    ) -> None:
        async with with_app_ctx(app_settings):
            with monkeypatch.context() as mp:
                mp.setattr(
                    AsyncClient,
                    "post",
                    create_async_function(
                        lambda *args, **kwargs: FakeResponse(
                            data={
                                "access_token": "token",
                                "refresh_token": "refresh_token",
                            },
                            status_code=200,
                        )
                    ),
                )
                access_token, refresh_token = await oauth_util.get_social_token(
                    code="code",
                    redirect_uri="http://localhost:8080/social",
                    provider_type=oauth_util.ProviderTypeEnum.Spotify,
                )

                assert access_token == "token"
                assert refresh_token == "refresh_token"
