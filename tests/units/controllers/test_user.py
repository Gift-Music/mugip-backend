import io
import pytest_asyncio

from PIL import Image
from httpx import AsyncClient
from tests.helper import ensure_fresh_env, with_app_ctx, create_async_function
from tests.mock.user import create_user
from _pytest.monkeypatch import MonkeyPatch

from app.settings import AppSettings
from app.controllers import user as fastapi_user
from app.utils import remote_file as remote_file_util
from app.utils import auth


class TestUser:
    @pytest_asyncio.fixture(scope="class", autouse=True)
    async def _init_env(
        self,
        app_settings: AppSettings,
        app_client: AsyncClient,
    ) -> None:
        async with with_app_ctx(app_settings):
            await ensure_fresh_env()
            await create_user(app_client)
            await create_user(
                app_client=app_client,
                email="another_user@example.com",
                username="another_username",
                password="test_password",
                nickname="another_nickname",
            )
            await fastapi_user.follow_post_api(
                q=fastapi_user._UserFollowPostRequset(target_user_id=2), me_user_id=1
            )
            await fastapi_user.follow_post_api(
                q=fastapi_user._UserFollowPostRequset(target_user_id=1), me_user_id=2
            )

    async def test_user_put_me_api(
        self,
        app_client: AsyncClient,
        user_access_token: str,
    ) -> None:
        headers = {"Authorization": "Bearer " + user_access_token}
        resp = await app_client.put(
            "/user/",
            headers=headers,
            json={
                "nickname": "new_test_nickname",
                "profile_image_url": "this_is_new_profile_image_url",
            },
        )

        check_user = await app_client.get("/user/", headers=headers)

        assert resp.status_code == 200
        assert check_user.json().get("nickname") == "new_test_nickname"
        assert (
            check_user.json().get("last_profile_image_url")
            == "this_is_new_profile_image_url"
        )

    async def test_user_get_me_api(
        self, app_client: AsyncClient, user_access_token: str
    ) -> None:
        headers = {"Authorization": "Bearer " + user_access_token}
        resp = await app_client.get("/user/", headers=headers)

        assert resp.status_code == 200
        assert resp.json() is not None
        assert resp.json().get("email") == "default_email@example.com"

    async def test_user_get_api(
        self,
        app_client: AsyncClient,
        user_access_token: str,
    ) -> None:
        headers = {"Authorization": "Bearer " + user_access_token}
        resp = await app_client.get("/user/2", headers=headers)

        assert resp.status_code == 200
        assert resp.json().get("id") == 2
        assert resp.json().get("email") == "another_user@example.com"

    async def test_user_profile_image_post_api(
        self,
        app_client: AsyncClient,
        monkeypatch: MonkeyPatch,
        app_settings: AppSettings,
        user_access_token: str,
    ) -> None:
        headers = {"Authorization": "Bearer " + user_access_token}

        # Create a temporary image file
        image = Image.new("RGB", (100, 100), color="red")
        file = io.BytesIO()
        image.save(file, format="JPEG")
        file.name = "test.jpg"
        file.seek(0)

        async with with_app_ctx(app_settings):
            with monkeypatch.context() as mp:
                mp.setattr(
                    remote_file_util,
                    "upload_profile_image",
                    (
                        lambda *arg, **kwargs: "some_aws_s3_url/uploaded_profile_image_name"
                    ),
                )

                resp = await app_client.post(
                    "/user/profile_image",
                    headers=headers,
                    files={"profile_file": (file.name, file)},
                )

        assert resp.status_code == 200

    async def test_user_search_post_api(
        self,
        app_client: AsyncClient,
        app_settings: AppSettings,
        user_access_token: str,
    ) -> None:
        headers = {"Authorization": "Bearer " + user_access_token}

        resp = await app_client.post(
            "/user/search", headers=headers, json={"offset": 0, "count": 10}
        )

        assert resp.status_code == 200
        assert resp.json() is not None
        assert len(resp.json()) == 2

        # filter by nickname
        filter_expr = {"nickname": "another_nickname"}
        resp = await app_client.post(
            "/user/search",
            headers=headers,
            json={"filter_expr": filter_expr, "offset": 0, "count": 10},
        )

        assert resp.status_code == 200
        assert resp.json() is not None
        assert len(resp.json()) == 1
        assert resp.json()[0]["nickname"] == "another_nickname"

        # filter by nickname (using ilike)
        filter_expr = {"nickname": "%nick%"}
        resp = await app_client.post(
            "/user/search",
            headers=headers,
            json={"filter_expr": filter_expr, "offset": 0, "count": 10},
        )

        assert resp.status_code == 200
        assert resp.json() is not None
        assert len(resp.json()) == 2

        # filter by email
        filter_expr = {"email": "default_email@example.com"}
        resp = await app_client.post(
            "/user/search",
            headers=headers,
            json={"filter_expr": filter_expr, "offset": 0, "count": 10},
        )

        assert resp.status_code == 200
        assert resp.json() is not None
        assert len(resp.json()) == 1
        assert resp.json()[0]["email"] == "default_email@example.com"

        # filter by email (using ilike)
        filter_expr = {"email": "%example%"}
        resp = await app_client.post(
            "/user/search",
            headers=headers,
            json={"filter_expr": filter_expr, "offset": 0, "count": 10},
        )

        assert resp.status_code == 200
        assert resp.json() is not None
        assert len(resp.json()) == 2

        # changing sort
        resp = await app_client.post(
            "/user/search",
            headers=headers,
            json={
                "sort_by_key": "nickname",
                "sort_by_order": "desc",
                "offset": 0,
                "count": 10,
            },
        )

        assert resp.status_code == 200
        assert resp.json() is not None
        assert len(resp.json()) == 2

    async def test_user_followers_get_api(
        self,
        app_client: AsyncClient,
        user_access_token: str,
    ) -> None:
        headers = {"Authorization": "Bearer " + user_access_token}
        resp = await app_client.get(
            "/user/followers", headers=headers, params={"offset": 0, "count": 10}
        )

        assert resp.status_code == 200
        assert resp.json() is not None
        assert resp.json()[0].get("id") == 2

    async def test_user_following_get_api(
        self,
        app_client: AsyncClient,
        user_access_token: str,
    ) -> None:
        headers = {"Authorization": "Bearer " + user_access_token}
        resp = await app_client.get(
            "/user/followings", headers=headers, params={"offset": 0, "count": 10}
        )

        assert resp.status_code == 200
        assert resp.json() is not None
        assert resp.json()[0].get("id") == 2


class TestUserFail:
    pass
