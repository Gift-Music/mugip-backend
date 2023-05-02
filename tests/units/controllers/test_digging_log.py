import pytest
import pytest_asyncio

from httpx import AsyncClient
from tests.helper import ensure_fresh_env, with_app_ctx
from tests.mock.digging_log import create_digging_log
from tests.mock.user import create_user

from app.settings import AppSettings
from app.controllers import digging_log as fastapi_digging_log
from app.utils import fastapi as fastapi_util


class TestDiggingLog:
    @pytest_asyncio.fixture(scope="class", autouse=True)
    async def _init_env(
        self,
        app_settings: AppSettings,
        app_client: AsyncClient,
    ) -> None:
        async with with_app_ctx(app_settings):
            await ensure_fresh_env()
            await create_user()
            await create_digging_log()

    async def test_digging_log_post_api(
        self,
        app_client: AsyncClient,
        user_access_token: str,
    ) -> None:
        headers = {"Authorization": "Bearer " + user_access_token}
        resp = await app_client.post(
            "/digging_log/",
            headers=headers,
            json={
                "track_id": "4fouWK6XVHhzl78KzQ1UjL",
                "tag_name": "test_tag",
                "coordinates": [0.1, 0.2],
            },
        )

        assert resp.status_code == 200

        resp = await app_client.post(
            "/digging_log/",
            headers=headers,
            json={
                "track_id": "1pFgar9U2S5FfrNdnSVOJK",
                "tag_name": "test_tag",
                "coordinates": [0.1, 0.2],
            },
        )

        assert resp.status_code == 200

    async def test_digging_log_search_api(
        self,
        app_client: AsyncClient,
        user_access_token: str,
    ) -> None:
        headers = {"Authorization": "Bearer " + user_access_token}
        filter_expr = {"tag_name": "test%"}
        resp = await app_client.post(
            "/digging_log/search",
            headers=headers,
            json={"filter_expr": filter_expr, "offset": 0, "count": 10},
        )

        assert resp.status_code == 200
        assert resp.json() is not None

        # album
        assert (resp.json() or {})[0].get("track", {}).get("album", {}).get("name", {}) == "abcdefu"

        # image
        assert (resp.json() or {})[0].get("track", {}).get("album", {}).get("images", {}) is not None

        # artist
        assert (resp.json() or {})[0].get("track", {}).get("artists", {})[0].get("name", {}) == "GAYLE"

        # user
        assert (resp.json() or {})[0].get("user", {}).get("nickname", {}) == "nickname"

        # tag
        assert (resp.json() or {})[0].get("tags", {})[0].get("name", {}) == "test_tag"


class TestDiggingLogFail:
    @pytest_asyncio.fixture(scope="class", autouse=True)
    async def _init_env(
        self,
        app_settings: AppSettings,
    ) -> None:
        async with with_app_ctx(app_settings):
            await ensure_fresh_env()
            await create_user()
            await create_digging_log()

    @pytest.mark.parametrize(
        "expected_error_code, expected_error_message",
        [("not_found_tag", "failed to found tag by this name")],
    )
    async def test_digging_log_post_api_fail_not_found_tag(
        self,
        app_client: AsyncClient,
        expected_error_code: str | None,
        expected_error_message: str | None,
        user_access_token: str,
    ) -> None:
        headers = {"Authorization": "Bearer " + user_access_token}
        fail_resp = await app_client.post(
            "/digging_log/",
            headers=headers,
            json={
                "track_id": "4fouWK6XVHhzl78KzQ1UjL",
                "tag_name": "invalid_tag_name",
                "coordinates": [0.1, 0.2],
            },
        )

        assert (fail_resp.json() or {}).get("detail", {}).get(
            "code"
        ) == expected_error_code
        assert (fail_resp.json() or {}).get("detail", {}).get(
            "message"
        ) == expected_error_message
    
    @pytest.mark.parametrize(
        "expected_error_code, expected_error_message",
        [("not_found_user", "failed to found user by this id")],
    )
    async def test_digging_log_post_api_fail_not_found_user(
        self,
        app_settings: AppSettings,
        expected_error_code: str | None,
        expected_error_message: str | None,
    ) -> None:
        async with with_app_ctx(app_settings): 
            with pytest.raises(fastapi_util.LogicError) as err:
                q = fastapi_digging_log._DiggingLogPostRequest(track_id='4fouWK6XVHhzl78KzQ1UjL', tag_name='test_tag', coordinates=[0.1, 0.2])
                await fastapi_digging_log.digging_log_post_api(q=q, me_user_id=0)

        assert err.value.code == expected_error_code
        assert err.value.message == expected_error_message

    @pytest.mark.parametrize(
        "expected_error_code, expected_error_message",
        [("filter_expr", "value_error")],
    )
    async def test_digging_log_search_api_fail_invalid_filter_expr(
        self,
        app_client: AsyncClient,
        expected_error_code: str | None,
        expected_error_message: str | None,
        user_access_token: str,
    ) -> None:
        headers = {
            "Authorization": "Bearer " + user_access_token,
        }
        filter_expr = {"wrong_expr": "wrong_filter_value"}
        fail_resp = await app_client.post(
            "/digging_log/search",
            headers=headers,
            json={"filter_expr": filter_expr, "offset": 0, "count": 10},
        )

        assert (fail_resp.json() or {}).get("detail", {})[0].get("loc")[
            1
        ] == expected_error_code
        assert (fail_resp.json() or {}).get("detail", {})[0].get(
            "type"
        ) == expected_error_message