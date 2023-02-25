import pytest
import pytest_asyncio

from httpx import AsyncClient
from tests.helper import ensure_fresh_env, with_app_ctx
from tests.mock.user import create_user
from tests.mock.tag import create_tag

from app.settings import AppSettings


class TestTag:
    @pytest_asyncio.fixture(scope="class", autouse=True)
    async def _init_env(
        self,
        app_settings: AppSettings,
        app_client: AsyncClient,
    ) -> None:
        async with with_app_ctx(app_settings):
            await ensure_fresh_env()
            await create_user(app_client)
            await create_tag()

    async def test_tag_post_api(
        self,
        app_client: AsyncClient,
        user_access_token: str,
    ) -> None:
        headers = {"Authorization": "Bearer " + user_access_token}

        resp = await app_client.post(
            "/tag/",
            headers=headers,
            json={"name": "new_tag_name", "icon": "new_tag_icon"},
        )

        assert resp.status_code == 200

        filter_expr = {"name": "new_tag_name"}
        check_tag = await app_client.post(
            "/tag/search",
            headers=headers,
            json={"filter_expr": filter_expr, "offset": 0, "count": 10},
        )

        assert check_tag.status_code == 200
        assert check_tag.json() is not None
        assert check_tag.json()[0].get("name") == "new_tag_name"

    async def test_tag_search_api(
        self,
        app_client: AsyncClient,
        user_access_token: str,
    ) -> None:
        headers = {"Authorization": "Bearer " + user_access_token}
        filter_expr = {"name": "test%"}

        resp = await app_client.post(
            "/tag/search",
            headers=headers,
            json={"filter_expr": filter_expr, "offset": 0, "count": 10},
        )

        assert resp.status_code == 200
        assert resp.json() is not None
        assert resp.json()[0].get("name") == "test_tag"


class TestTagFail:
    @pytest_asyncio.fixture(scope="class", autouse=True)
    async def _init_env(
        self,
        app_settings: AppSettings,
        app_client: AsyncClient,
    ) -> None:
        async with with_app_ctx(app_settings):
            await ensure_fresh_env()
            await create_user(app_client)
            await create_tag()

    @pytest.mark.parametrize(
        "expected_error_code, expected_error_message",
        [("model_already_eixsts", "model is already exists")],
    )
    async def test_tag_post_api_fail_already_exist_tag(
        self,
        app_client: AsyncClient,
        expected_error_code: str | None,
        expected_error_message: str | None,
        user_access_token: str,
    ) -> None:
        headers = {"Authorization": "Bearer " + user_access_token}

        fail_resp = await app_client.post('/tag/', headers=headers, json={"name":"test_tag", "icon":"test_tag_icon"})

        assert (fail_resp.json() or {}).get("detail", {}).get(
            "code"
        ) == expected_error_code
        assert (fail_resp.json() or {}).get("detail", {}).get(
            "message"
        ) == expected_error_message

    @pytest.mark.parametrize(
        "expected_error_code, expected_error_message",
        [("filter_expr", "value_error")],
    )
    async def test_tag_search_api_fail_invalid_filter_expr(
        self,
        app_client: AsyncClient,
        expected_error_code: str | None,
        expected_error_message: str | None,
        user_access_token: str,
    ) -> None:
        headers = {"Authorization": "Bearer " + user_access_token}
        invalid_filter_expr = {"invalid_filter_naming": "invalid_name"}

        fail_resp = await app_client.post(
            "/tag/search",
            headers=headers,
            json={"filter_expr": invalid_filter_expr, "offset": 0, "count": 10},
        )

        assert (fail_resp.json() or {}).get("detail", {})[0].get("loc")[
            1
        ] == expected_error_code
        assert (fail_resp.json() or {}).get("detail", {})[0].get(
            "type"
        ) == expected_error_message
