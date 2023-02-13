import pytest_asyncio
import pytest
import jwt

from tests.helper import with_app_ctx, ensure_fresh_env
from app.settings import AppSettings
from httpx import AsyncClient
from _pytest.monkeypatch import MonkeyPatch
from tests.helper import FakeResponse, create_async_function

from sqlalchemy.exc import IntegrityError

from app.utils import oauth as oauth_util
from app.utils import auth as auth_util
from app.utils import fastapi as fastapi_util
from app import ctx
from app.controllers import auth as fastapi_auth
from tests.mock.user import create_user, create_social_user


class TestAuth:
    @pytest_asyncio.fixture(scope="class", autouse=True)
    async def _init_env(self, app_settings: AppSettings) -> None:
        async with with_app_ctx(app_settings):
            await ensure_fresh_env()

    async def test_auth_signup_api(
        self,
        app_client: AsyncClient,
    ) -> None:
        resp = await create_user(
            app_client=app_client,
            username="test",
            nickname="test",
            password="test_password",
            email="test@example.com",
        )
        assert resp.status_code == 200

    async def test_auth_login_api(
        self,
        app_client: AsyncClient,
    ) -> None:
        # Test: Happy case
        resp = await app_client.post(
            "/auth/login",
            json={
                "email": "test@example.com",
                "password": "test_password",
            },
        )

        assert resp.status_code == 200
        assert resp.json()["access_token"] is not None
        assert resp.json()["refresh_token"] is not None

    async def test_auth_oauth_login_api(
        self,
        app_client: AsyncClient,
    ) -> None:
        await create_user(app_client=app_client)
        resp = await app_client.post(
            "/auth/login/oauth",
            data={
                "username": "default_email@example.com",
                "password": "default_password",
            },
        )

        assert resp.status_code == 200
        assert resp.json()["access_token"] is not None
        assert resp.json()["refresh_token"] is not None

    @pytest.mark.parametrize(
        "social_access_token, social_refresh_token",
        [("socialapp_access_token", "socialapp_refresh_token")],
    )
    async def test_auth_social_signup_api(
        self,
        app_client: AsyncClient,
        monkeypatch: MonkeyPatch,
        app_settings: AppSettings,
        social_access_token: str | None,
        social_refresh_token: str | None,
    ) -> None:
        async with with_app_ctx(app_settings):
            with monkeypatch.context() as mp:
                mp.setattr(
                    oauth_util,
                    "get_social_token",
                    create_async_function(
                        lambda *args, **kwargs: (
                            social_access_token,
                            social_refresh_token,
                        )
                    ),
                ),
                mp.setattr(
                    oauth_util,
                    "get_social_info",
                    create_async_function(
                        lambda *args, **kwargs: oauth_util.SocialInfo(
                            uid="social_uid",
                            email="social_email@example.com",
                            name="social_name",
                        )
                    ),
                )
                resp = await app_client.post(
                    "/auth/signup/social",
                    json={
                        "code": "code",
                        "redirect_uri": "http://localhost:8080/social",
                        "provider_type": oauth_util.ProviderTypeEnum.Spotify,
                    },
                )

        assert resp.status_code == 200
        assert resp.json()["access_token"] is not None
        assert resp.json()["refresh_token"] is not None
        assert resp.json()["social_access_token"] == social_access_token
        assert resp.json()["social_refresh_token"] == social_refresh_token

    @pytest.mark.parametrize(
        "social_access_token, social_refresh_token",
        [("socialapp_access_token", "socialapp_refresh_token")],
    )
    async def test_auth_social_login(
        self,
        app_client: AsyncClient,
        monkeypatch: MonkeyPatch,
        app_settings: AppSettings,
        social_access_token: str | None,
        social_refresh_token: str | None,
    ) -> None:
        async with with_app_ctx(app_settings) as current_ctx:
            await create_social_user(
                app_ctx=current_ctx,
                email="new_social_user@example.com",
                display_name="new_social_user_name",
            )
            with monkeypatch.context() as mp:
                mp.setattr(
                    oauth_util,
                    "get_social_token",
                    create_async_function(
                        lambda *args, **kwargs: (
                            social_access_token,
                            social_refresh_token,
                        )
                    ),
                ),
                mp.setattr(
                    oauth_util,
                    "get_social_info",
                    create_async_function(
                        lambda *args, **kwargs: oauth_util.SocialInfo(
                            uid="default_user_uid",
                            email="new_social_email@example.com",
                            name="new_social_name",
                        )
                    ),
                )
                resp = await app_client.post(
                    "/auth/login/social",
                    json={
                        "code": "code",
                        "redirect_uri": "http://localhost:8080/social",
                        "provider_type": oauth_util.ProviderTypeEnum.Spotify,
                    },
                )

        assert resp.status_code == 200
        assert resp.json()["access_token"] is not None
        assert resp.json()["refresh_token"] is not None
        assert resp.json()["social_access_token"] == social_access_token
        assert resp.json()["social_refresh_token"] == social_refresh_token

    async def test_auth_refresh(
        self,
        app_client: AsyncClient,
        monkeypatch: MonkeyPatch,
        app_settings: AppSettings,
    ) -> None:
        async with with_app_ctx(app_settings):
            with monkeypatch.context() as mp:
                mp.setattr(jwt, "decode", lambda *args, **kwargs: {"user_id": 1})
                resp = await app_client.post(
                    "/auth/refresh",
                    json={
                        "refresh_token": "expired_refresh_token",
                    },
                )

        assert resp.status_code == 200
        assert resp.json()["access_token"] is not None
        assert resp.json()["refresh_token"] is not None

    async def test_auth_guest_login(
        self,
        app_client: AsyncClient,
    ) -> None:
        resp = await app_client.post(
            "/auth/login/guest",
            json={
                "nickname": "this_is_guest",
                "is_agreed": True,
            },
        )

        assert resp.status_code == 200
        assert resp.json()["access_token"] is not None
        assert resp.json()["refresh_token"] is not None


class TestAuthFail:
    @pytest_asyncio.fixture(scope="class", autouse=True)
    async def _init_env(self, app_settings: AppSettings) -> None:
        async with with_app_ctx(app_settings):
            await ensure_fresh_env()

    @pytest.mark.parametrize(
        "expected_error_code, expected_error_message",
        [("already_exist_email", "already exist email")],
    )
    async def test_auth_signup_api_fail_already_registered(
        self,
        app_client: AsyncClient,
        monkeypatch: MonkeyPatch,
        app_settings: AppSettings,
        expected_error_code: str | None,
        expected_error_message: str | None,
    ) -> None:
        await create_user(
            app_client=app_client,
            username="test",
            password="test_password",
            nickname="test",
            email="test@example.com",
        )
        async with with_app_ctx(app_settings):
            with monkeypatch.context() as mp:
                mp.setattr(
                    ctx, "_current_app_ctx_getter", lambda: "here's current contexts"
                )

            request_query = fastapi_auth._SignUpRequest(
                email="test@example.com",
                username="test",
                nickname="test",
                password="test_password",
                is_agreed=True,
            )

            with pytest.raises(fastapi_util.LogicError) as err:
                fail_resp = await fastapi_auth.signup_api(q=request_query)

            assert err.value.code == expected_error_code
            assert err.value.message == expected_error_message

    @pytest.mark.parametrize(
        "expected_error_code, expected_error_message",
        [("try_again", "there is a race condition. try again.")],
    )
    @pytest.mark.skip(reason="implement later...")
    async def test_auth_signup_api_fail_integrity_error(
        self,
        app_client: AsyncClient,
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
                        lambda: IntegrityError(
                            statement="integrity error", params="", orig=None
                        ),
                    ),
                )

            request_query = fastapi_auth._SignUpRequest(
                email="test@example.com",
                username="test",
                nickname="test",
                password="test_password",
                is_agreed=True,
            )

    @pytest.mark.parametrize(
        "expected_error_code, expected_error_message",
        [("not_found_user", "failed to found user by this email")],
    )
    async def test_auth_login_api_fail_no_user(
        self,
        app_client: AsyncClient,
        monkeypatch: MonkeyPatch,
        app_settings: AppSettings,
        expected_error_code: str | None,
        expected_error_message: str | None,
    ) -> None:
        async with with_app_ctx(app_settings):
            with monkeypatch.context() as mp:
                mp.setattr(
                    ctx, "_current_app_ctx_getter", lambda: "here's current contexts"
                ),

            request_query = fastapi_auth._LoginRequest(
                email="wrong_user@example.com",
                password="test_password",
            )

            with pytest.raises(fastapi_util.LogicError) as err:
                fail_resp = await fastapi_auth.login_api(q=request_query)

            assert err.value.code == expected_error_code
            assert err.value.message == expected_error_message

    @pytest.mark.parametrize(
        "expected_error_code, expected_error_message",
        [("invalid_password", "this password is not valid")],
    )
    async def test_auth_login_api_fail_invalid_pw(
        self,
        app_client: AsyncClient,
        monkeypatch: MonkeyPatch,
        app_settings: AppSettings,
        expected_error_code: str | None,
        expected_error_message: str | None,
    ) -> None:
        async with with_app_ctx(app_settings):
            with monkeypatch.context() as mp:
                mp.setattr(
                    ctx, "_current_app_ctx_getter", lambda: "here's current contexts"
                ),

            request_query = fastapi_auth._LoginRequest(
                email="test@example.com",
                password="wrong_password",
            )

            with pytest.raises(fastapi_util.LogicError) as err:
                fail_resp = await fastapi_auth.login_api(q=request_query)

            assert err.value.code == expected_error_code
            assert err.value.message == expected_error_message
