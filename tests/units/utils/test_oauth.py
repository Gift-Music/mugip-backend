import pytest_asyncio
import pytest
from tests.helper import with_app_ctx, ensure_fresh_env
from app.settings import AppSettings
from httpx import AsyncClient
from app.utils import oauth as oauth_util
from _pytest.monkeypatch import MonkeyPatch
from tests.helper import FakeResponse, create_async_function


class TestOAuth:
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

    @pytest.mark.parametrize(
        "social_id, social_email, social_name",
        [("social_test_id", "social_test_email", "social_display_name")],
    )
    async def test_get_social_info(
        self,
        monkeypatch: MonkeyPatch,
        app_settings: AppSettings,
        social_id: str | None,
        social_email: str | None,
        social_name: str | None,
    ) -> None:
        async with with_app_ctx(app_settings):
            with monkeypatch.context() as mp:
                mp.setattr(
                    AsyncClient,
                    "get",
                    create_async_function(
                        lambda *args, **kwargs: FakeResponse(
                            data={
                                "id": social_id,
                                "email": social_email,
                                "display_name": social_name,
                            },
                            status_code=200,
                        )
                    ),
                )
                resp = await oauth_util.get_social_info(
                    token="token",
                    provider_type=oauth_util.ProviderTypeEnum.Spotify,
                )

                assert type(resp) == oauth_util.SocialInfo
                assert resp.uid == social_id
                assert resp.email == social_email
                assert resp.name == social_name


class TestOAuthFail:
    @pytest_asyncio.fixture(scope="class", autouse=True)
    async def _init_env(self, app_settings: AppSettings) -> None:
        async with with_app_ctx(app_settings):
            await ensure_fresh_env()

    @pytest.mark.parametrize(
        "expected_error_code, expected_error_message",
        [("invalid_provider_type", "provider_type is not valid")],
    )
    async def test_get_social_token_fail(
        self,
        expected_error_code: str | None,
        expected_error_message: str | None,
    ) -> None:
        with pytest.raises(oauth_util.OauthUtilError) as err:
            await oauth_util.get_social_token(
                code="code",
                redirect_uri="http://localhost:8080/social",
                provider_type="invalid_provider",
            )

        assert err.value.code == expected_error_code
        assert err.value.message == expected_error_message

    @pytest.mark.parametrize(
        "expected_error_code, expected_error_message",
        [("failed_to_fetch_spotify_token", "something wrong")],
    )
    async def test_get_spotify_token_fail(
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
                    "post",
                    create_async_function(
                        lambda *args, **kwargs: FakeResponse(
                            data={
                                "item": "something returned message"
                            },
                            status_code=400,
                        )
                    ),
                )
            with pytest.raises(oauth_util.OauthUtilError) as err:
                await oauth_util.spotify_get_token(
                    code="invalid_code", redirect_uri="http://localhost:8080/social"
                )

            assert err.value.code == expected_error_code
            assert err.value.message == expected_error_message

    @pytest.mark.parametrize(
        "expected_error_code, expected_error_message",
        [("invalid_provider_type", "provider_type is not valid")],
    )
    async def test_get_social_info_fail(
        self,
        expected_error_code: str | None,
        expected_error_message: str | None,
    ) -> None:
        with pytest.raises(oauth_util.OauthUtilError) as err:
            await oauth_util.get_social_info(
                token="test_token",
                provider_type="invalid_provider",
            )

        assert err.value.code == expected_error_code
        assert err.value.message == expected_error_message
