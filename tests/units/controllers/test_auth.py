import pytest_asyncio
import pytest
import jwt

from app.settings import AppSettings
from httpx import AsyncClient
from _pytest.monkeypatch import MonkeyPatch
from tests.helper import create_async_function, with_app_ctx, ensure_fresh_env
from fastapi.security import OAuth2PasswordRequestForm

from app.utils import oauth as oauth_util
from app.utils import fastapi as fastapi_util
from app.models import postgres as m
from app import ctx
from app.ctx import AppCtx
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
                        "refresh_token": "this_is_refresh_token",
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
                await fastapi_auth.signup_api(q=request_query)

            assert err.value.code == expected_error_code
            assert err.value.message == expected_error_message

    @pytest.mark.parametrize(
        "expected_error_code, expected_error_message",
        [("try_again", "there is a race condition. try again.")],
    )
    async def test_auth_signup_api_fail_integrity_error(
        self,
        monkeypatch: MonkeyPatch,
        app_settings: AppSettings,
        expected_error_code: str | None,
        expected_error_message: str | None,
    ) -> None:
        async with with_app_ctx(app_settings) as app_ctx:
            with monkeypatch.context() as mp:
                mp.setattr(
                    AppCtx.current.db.session,
                    "scalar",
                    create_async_function(
                        lambda *args, **kwargs: False,
                    ),
                )
                user = m.User(
                    email="test@example.com",
                    username="test",
                    nickname="test",
                    password="test_password",
                )
                app_ctx.current.db.session.add(user)
                request_query = fastapi_auth._SignUpRequest(
                    email=user.email,
                    username=user.username,
                    nickname=user.nickname,
                    password=user.password,
                    is_agreed=True,
                )
                with pytest.raises(fastapi_util.LogicError) as err:
                    await fastapi_auth.signup_api(q=request_query)

        assert err.value.code == expected_error_code
        assert err.value.message == expected_error_message

    @pytest.mark.parametrize(
        "expected_error_code, expected_error_message",
        [("not_found_user", "failed to found user by this email")],
    )
    async def test_auth_login_api_fail_no_user(
        self,
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
                    await fastapi_auth.login_api(q=request_query)

        assert err.value.code == expected_error_code
        assert err.value.message == expected_error_message

    @pytest.mark.parametrize(
        "expected_error_code, expected_error_message",
        [("invalid_password", "this password is not valid")],
    )
    async def test_auth_login_api_fail_invalid_pw(
        self,
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
                await fastapi_auth.login_api(q=request_query)

            assert err.value.code == expected_error_code
            assert err.value.message == expected_error_message

    @pytest.mark.parametrize(
        "expected_error_code, expected_error_message",
        [("not_found_user", "failed to found user by this email")],
    )
    async def test_auth_oauth_login_api_fail_no_user(
        self,
        monkeypatch: MonkeyPatch,
        app_settings: AppSettings,
        expected_error_code: str | None,
        expected_error_message: str | None,
    ) -> None:
        async with with_app_ctx(app_settings):
            with monkeypatch.context() as mp:
                mp.setattr(
                    ctx, "_current_app_ctx_getter", lambda: "here's current contexts"
                )
                q = OAuth2PasswordRequestForm(username="wrong_user@example.com", password="test_password", scope="")
                with pytest.raises(fastapi_util.LogicError) as err:
                    await fastapi_auth.login_oauth_api(q=q)

        assert err.value.code == expected_error_code
        assert err.value.message == expected_error_message

    @pytest.mark.parametrize(
        "expected_error_code, expected_error_message",
        [("invalid_password", "this password is not valid")],
    )
    async def test_auth_oauth_login_api_fail_invalid_pw(
        self,
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

            q = OAuth2PasswordRequestForm(username="test@example.com", password="wrong_password", scope="")

            with pytest.raises(fastapi_util.LogicError) as err:
                await fastapi_auth.login_oauth_api(q=q)

        assert err.value.code == expected_error_code
        assert err.value.message == expected_error_message

    async def test_auth_social_signup_api_fail(
        self,
        monkeypatch: MonkeyPatch,
        app_settings: AppSettings,
    ) -> None:
        async with with_app_ctx(app_settings):
            with monkeypatch.context() as mp:
                mp.setattr(
                    ctx, "_current_app_ctx_getter", lambda: "here's current contexts"
                ),
                q = fastapi_auth._SocialSignUpRequest(code="code", redirect_uri="red_uri_here", provider_type=oauth_util.ProviderTypeEnum.Spotify)
                with pytest.raises(fastapi_util.LogicError) as err:
                    await fastapi_auth.social_signup_api(q=q)

        assert err.value.code is not None
        assert err.value.message is not None
        
    @pytest.mark.parametrize(
        "expected_error_code, expected_error_message",
        [("already_exist_uid", "Already signed up user")],
    )
    async def test_auth_social_signup_api_fail_user_alredy_exist(
        self,
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
                mp.setattr(
                    oauth_util,
                    "get_social_token",
                    create_async_function(
                        lambda *args, **kwargs: (
                            "social_access_token",
                            "social_refresh_token",
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
                ),
                mp.setattr(
                    AppCtx.current.db.session,
                    "scalar",
                    create_async_function(
                        lambda *args, **kwargs: True,
                    ),
                )
                
                q = fastapi_auth._SocialSignUpRequest(code="code", redirect_uri="red_uri_here", provider_type=oauth_util.ProviderTypeEnum.Spotify)
                with pytest.raises(fastapi_util.LogicError) as err:
                    await fastapi_auth.social_signup_api(q=q)

        assert err.value.code == expected_error_code
        assert err.value.message == expected_error_message

    async def test_auth_social_signin_api_fail(
        self,
        monkeypatch: MonkeyPatch,
        app_settings: AppSettings,
    ) -> None:
        async with with_app_ctx(app_settings):
            with monkeypatch.context() as mp:
                mp.setattr(
                    ctx, "_current_app_ctx_getter", lambda: "here's current contexts"
                ),
                q = fastapi_auth._SocialLoginRequest(code="code", redirect_uri="red_uri_here", provider_type=oauth_util.ProviderTypeEnum.Spotify)
                with pytest.raises(oauth_util.OauthUtilError) as err:
                    await fastapi_auth.social_login_api(q=q)

        assert err.value.code is not None
        assert err.value.message is not None
        assert err.value.detail is not None

    @pytest.mark.parametrize(
        "expected_error_code, expected_error_message",
        [("not_found_user", "failed to found user by this email")],
    )
    async def test_auth_social_signin_api_fail_no_user(
        self,
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
                mp.setattr(
                    oauth_util,
                    "get_social_token",
                    create_async_function(
                        lambda *args, **kwargs: (
                            "social_access_token",
                            "social_refresh_token",
                        )
                    ),
                ),
                mp.setattr(
                    oauth_util,
                    "get_social_info",
                    create_async_function(
                        lambda *args, **kwargs: oauth_util.SocialInfo(
                            uid="wrong_user_uid",
                            email="wrong_email@example.com",
                            name="wrong_name",
                        )
                    ),
                ),
                q = fastapi_auth._SocialLoginRequest(code="code", redirect_uri="red_uri_here", provider_type=oauth_util.ProviderTypeEnum.Spotify)
                with pytest.raises(fastapi_util.LogicError) as err:
                    await fastapi_auth.social_login_api(q=q)

        assert err.value.code == expected_error_code
        assert err.value.message == expected_error_message

    @pytest.mark.parametrize(
        "expected_error_code, expected_error_message",
        [("token_is_expired", "refresh token is expired")],
    )
    async def test_auth_refresh_api_fail_refresh_token_exp(
        self,
        monkeypatch: MonkeyPatch,
        app_settings: AppSettings,
        expected_error_code: str | None,
        expected_error_message: str | None,
    ) -> None:

        def raise_exc():
            raise jwt.ExpiredSignatureError

        async with with_app_ctx(app_settings):
            with monkeypatch.context() as mp:
                mp.setattr(
                    ctx, "_current_app_ctx_getter", lambda: "here's current contexts"
                ),
                mp.setattr(
                    jwt, "decode", lambda *args, **kwargs: raise_exc()
                )
                q = fastapi_auth._AuthRefreshApiRequest(refresh_token="expired_refresh_token")
                with pytest.raises(fastapi_util.AuthError) as err:
                    await fastapi_auth.refresh_api(q=q)

        assert err.value.code == expected_error_code
        assert err.value.message == expected_error_message

    @pytest.mark.parametrize(
        "expected_error_code, expected_error_message",
        [("token_decode_failure", "failed to decode token")],
    )
    async def test_auth_refresh_api_fail_decode_err(
        self,
        monkeypatch: MonkeyPatch,
        app_settings: AppSettings,
        expected_error_code: str | None,
        expected_error_message: str | None,
    ) -> None:
        
        def raise_exc():
            raise jwt.DecodeError
        
        async with with_app_ctx(app_settings):
            with monkeypatch.context() as mp:
                mp.setattr(
                    ctx, "_current_app_ctx_getter", lambda: "here's current contexts"
                ),
                mp.setattr(
                    jwt, "decode", lambda *args, **kwargs: raise_exc()
                )
                q = fastapi_auth._AuthRefreshApiRequest(refresh_token="some_refresh_token")
                with pytest.raises(fastapi_util.AuthError) as err:
                    await fastapi_auth.refresh_api(q=q)

        assert err.value.code == expected_error_code
        assert err.value.message == expected_error_message

    @pytest.mark.parametrize(
        "expected_error_code, expected_error_message",
        [("invalid_token_structure", "token structure is invalid")],
    )
    async def test_auth_refresh_api_fail_invalid_token(
        self,
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
                mp.setattr(
                    jwt, "decode", lambda *args, **kwargs: {"user_id": "some_wrong_decoded_user_info"}
                )
                q = fastapi_auth._AuthRefreshApiRequest(refresh_token="wrong_refresh_token")
                with pytest.raises(fastapi_util.AuthError) as err:
                    await fastapi_auth.refresh_api(q=q)

        assert err.value.code == expected_error_code
        assert err.value.message == expected_error_message

    @pytest.mark.parametrize(
        "expected_error_code, expected_error_message",
        [("user_deleted", "user is not exists")],
    )
    async def test_auth_refresh_api_fail_no_user(
        self,
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
                mp.setattr(
                    jwt, "decode", lambda *args, **kwargs: {"user_id": 0}
                )
                q = fastapi_auth._AuthRefreshApiRequest(refresh_token="refresh_token")
                with pytest.raises(fastapi_util.AuthError) as err:
                    await fastapi_auth.refresh_api(q=q)

        assert err.value.code == expected_error_code
        assert err.value.message == expected_error_message
