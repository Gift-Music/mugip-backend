from httpx import AsyncClient

from tests import constants as test_c
from app.models import postgres as m
from app.ctx import AppCtx

from sqlalchemy.exc import IntegrityError
from app.utils import fastapi as fastapi_util
from app.utils import oauth as oauth_util


async def create_user(
    app_client: AsyncClient,
    username: str = test_c.DEFAULT_USERNAME,
    password: str = test_c.DEFAULT_USER_PASSWORD,
    nickname: str = "nickname",
    email: str = test_c.DEFAULT_USER_EMAIL,
) -> dict:
    resp = await app_client.post(
        "/auth/signup",
        json={
            "email": email,
            "username": username,
            "password": password,
            "nickname": nickname,
            "is_agreed": True,
        },
    )

    return resp

async def create_social_user(
    app_ctx: None = AppCtx,
    display_name: str = test_c.DEFAULT_USERNAME,
    social_uid: str = test_c.DEFAULT_USER_UID,
    email: str = test_c.DEFAULT_USER_EMAIL,
    provider_type: None = oauth_util.ProviderTypeEnum.Spotify,
) -> None:
    user = m.User(email=email, username=display_name, nickname=display_name)
    user_uid = m.UserOauthLogin(uid=social_uid, user=user, user_id=user.id, provider_type=provider_type)

    app_ctx.current.db.session.add(user)
    app_ctx.current.db.session.add(user_uid)

    try:
        await app_ctx.current.db.session.commit()
    except IntegrityError as ex:
        print(ex)
        raise fastapi_util.LogicError(
            code="try_again",
            message="there is a race condition. try again.",
        )
