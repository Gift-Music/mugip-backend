import io
import pytest
import pytest_asyncio

from PIL import Image
from httpx import AsyncClient
from tests.helper import ensure_fresh_env, with_app_ctx, create_async_function
from tests.mock.user import create_user
from _pytest.monkeypatch import MonkeyPatch

from app.settings import AppSettings
from app.controllers import user as fastapi_user
from app.utils import remote_file as remote_file_util
from app.utils import fastapi as fastapi_util


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
                    create_async_function(
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
    @pytest_asyncio.fixture(scope="class", autouse=True)
    async def _init_env(
        self,
        app_settings: AppSettings,
        app_client: AsyncClient,
    ) -> None:
        async with with_app_ctx(app_settings):
            await ensure_fresh_env()
            await create_user(app_client)

    @pytest.mark.parametrize(
        "expected_error_code, expected_error_message",
        [("not_found_user", "failed to found user by this id")],
    )
    async def test_user_get_api_fail_no_user(
        self,
        app_client: AsyncClient,
        expected_error_code: str | None,
        expected_error_message: str | None,
        user_access_token: str,
    ) -> None:
        headers = {
            "Authorization": "Bearer " + user_access_token,
        }

        fail_resp = await app_client.get("/user/0", headers=headers)

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
    async def test_user_profile_image_post_api_fail_no_user(
        self,
        app_settings: AppSettings,
        expected_error_code: str | None,
        expected_error_message: str | None,
    ) -> None:
        # Create a temporary image file
        image = Image.new("RGB", (100, 100), color="red")
        file = io.BytesIO()
        image.save(file, format="JPEG")
        file.name = "test.jpg"
        file.seek(0)

        async with with_app_ctx(app_settings):
            with pytest.raises(fastapi_util.LogicError) as err:
                await fastapi_user.user_profile_image_post_api(
                    profile_file=(file.name, file), me_user_id=0
                )

        assert err.value.code == expected_error_code
        assert err.value.message == expected_error_message

    @pytest.mark.parametrize(
        "expected_error_code, expected_error_message",
        [("profile_file_upload_error", "AWS s3 does not response")],
    )
    async def test_user_profile_image_post_api_fail_image_upload_err(
        self,
        app_client: AsyncClient,
        expected_error_code: str | None,
        expected_error_message: str | None,
        user_access_token: str,
        app_settings: AppSettings,
        monkeypatch: MonkeyPatch,
    ) -> None:
        headers = {
            "Authorization": "Bearer " + user_access_token,
        }

        # Create a temporary image file
        image = Image.new("RGB", (100, 100), color="red")
        file = io.BytesIO()
        image.save(file, format="JPEG")
        file.name = "test.jpg"
        file.seek(0)

        async with with_app_ctx(app_settings):
            with monkeypatch.context() as mp:

                def raise_runtime_error(*args, **kwargs):
                    raise RuntimeError("AWS s3 does not response")

                mp.setattr(
                    remote_file_util, "upload_profile_image", raise_runtime_error
                )

                # Error occurs also when no AWS client id & secret.
                fail_resp = await app_client.post(
                    "/user/profile_image",
                    headers=headers,
                    files={"profile_file": (file.name, file)},
                )

        assert (fail_resp.json() or {}).get("detail", {}).get(
            "code"
        ) == expected_error_code
        assert (fail_resp.json() or {}).get("detail", {}).get(
            "message"
        ) == expected_error_message

    @pytest.mark.parametrize(
        "expected_error_code, expected_error_message",
        [("cannot_open_profile", "you cannot open profile image")],
    )
    async def test_user_profile_image_post_api_fail_open_profile_err(
        self,
        app_client: AsyncClient,
        expected_error_code: str | None,
        expected_error_message: str | None,
        user_access_token: str,
        app_settings: AppSettings,
        monkeypatch: MonkeyPatch,
    ) -> None:
        headers = {
            "Authorization": "Bearer " + user_access_token,
        }

        # Create a temporary image file
        image = Image.new("RGB", (100, 100), color="red")
        file = io.BytesIO()
        image.save(file, format="JPEG")
        file.name = "test.jpg"
        file.seek(0)

        async with with_app_ctx(app_settings):
            with monkeypatch.context() as mp:

                def raise_error(*args, **kwargs):
                    raise Exception("Some Exception occurs.")

                mp.setattr(remote_file_util, "upload_profile_image", raise_error)

                # Error occurs also when no AWS client id & secret.
                fail_resp = await app_client.post(
                    "/user/profile_image",
                    headers=headers,
                    files={"profile_file": (file.name, file)},
                )

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
    async def test_user_search_post_api_fail_invalid_filter_expr(
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
            "/user/search",
            headers=headers,
            json={"filter_expr": filter_expr, "offset": 0, "count": 10},
        )

        assert (fail_resp.json() or {}).get("detail", {})[0].get("loc")[
            1
        ] == expected_error_code
        assert (fail_resp.json() or {}).get("detail", {})[0].get(
            "type"
        ) == expected_error_message

    @pytest.mark.parametrize(
        "expected_error_code, expected_error_message",
        [("not_found_user", "failed to found user by this id")],
    )
    async def test_follow_post_api_fail_no_user(
        self,
        app_client: AsyncClient,
        expected_error_code: str | None,
        expected_error_message: str | None,
        user_access_token: str,
    ) -> None:
        headers = {
            "Authorization": "Bearer " + user_access_token,
        }
        fail_resp = await app_client.post(
            "/user/follow",
            headers=headers,
            json={"target_user_id": 0},
        )

        assert (fail_resp.json() or {}).get("detail", {}).get(
            "code"
        ) == expected_error_code
        assert (fail_resp.json() or {}).get("detail", {}).get(
            "message"
        ) == expected_error_message
