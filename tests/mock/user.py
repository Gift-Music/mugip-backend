from httpx import AsyncClient

from tests import constants as test_c


async def create_user(
    app_client: AsyncClient,
    username: str = test_c.DEFAULT_USERNAME,
    password: str = test_c.DEFAULT_USER_PASSWORD,
    email: str = test_c.DEFAULT_USER_EMAIL,
) -> None:
    resp = await app_client.post(
        "/auth/signup",
        json={
            "email": email,
            "username": username,
            "password": password,
            "nickname": "nickname",
            "is_agreed": True,
        },
    )

    assert resp.status_code == 200
