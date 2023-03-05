from httpx import AsyncClient

from tests import constants as test_c
from app.models import postgres as m
from app.ctx import AppCtx

from sqlalchemy.exc import IntegrityError
from app.utils import fastapi as fastapi_util
from app.utils import auth as auth_util
from app.utils import oauth as oauth_util


async def create_user(
    username: str = test_c.DEFAULT_USERNAME,
    password: str = test_c.DEFAULT_USER_PASSWORD,
    nickname: str = "nickname",
    email: str = test_c.DEFAULT_USER_EMAIL,
) -> None:
    user = m.User(
        email=email,
        username=username,
        nickname=nickname,
        password=await auth_util.generate_hashed_password(
            password
        ),
    )

    AppCtx.current.db.session.add(user)
    try:
        await AppCtx.current.db.session.commit()
    except IntegrityError as ex:
        print(ex)
        raise fastapi_util.LogicError(
            code="try_again",
            message="there is a race condition. try again.",
        )

async def create_social_user(
    display_name: str = test_c.DEFAULT_USERNAME,
    social_uid: str = test_c.DEFAULT_USER_UID,
    email: str = test_c.DEFAULT_USER_EMAIL,
    provider_type: None = oauth_util.ProviderTypeEnum.Spotify,
) -> None:
    user = m.User(email=email, username=display_name, nickname=display_name)
    user_uid = m.UserOauthLogin(uid=social_uid, user=user, user_id=user.id, provider_type=provider_type)

    AppCtx.current.db.session.add(user)
    AppCtx.current.db.session.add(user_uid)

    try:
        await AppCtx.current.db.session.commit()
    except IntegrityError as ex:
        print(ex)
        raise fastapi_util.LogicError(
            code="try_again",
            message="there is a race condition. try again.",
        )
