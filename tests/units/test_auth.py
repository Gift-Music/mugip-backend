import pytest_asyncio
import pytest
from tests.helper import with_app_ctx, ensure_fresh_env
from app.settings import AppSettings
from httpx import AsyncClient


class TestAuth:
    @pytest_asyncio.fixture(scope="class", autouse=True)
    async def _init_env(self, app_settings: AppSettings) -> None:
        async with with_app_ctx(app_settings):
            await ensure_fresh_env()

    @pytest.mark.parametrize(
        "expected_error_code",
        [None, "already_exist_email"],
    )
    async def test_auth_signup_api(
        self,
        app_client: AsyncClient,
        expected_error_code: str | None,
    ) -> None:
        resp = await app_client.post(
            "/auth/signup",
            json={
                "email": "test@example.com",
                "username": "test",
                "nickname": "test",
                "password": "test_password",
                "is_agreed": True,
            },
        )
        assert (
            (resp.json() or {})
            .get("detail", {})
            .get("code") == expected_error_code
        )

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
