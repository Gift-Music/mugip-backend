import jwt
from fastapi import Depends
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, SecretStr
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import expression as sql_exp

from app.ctx import AppCtx
from app.models import postgres as m
from app.utils import auth as auth_util
from app.utils import fastapi as fastapi_util
from app.utils import oauth as oauth_util
from app.utils.fastapi import CustomAPIRouter

router = CustomAPIRouter(prefix="/auth", tags=["auth"])


class _SignUpRequest(BaseModel):
    email: EmailStr
    nickname: str
    password: SecretStr
    is_agreed: bool


@router.post("/signup")
async def signup_api(q: _SignUpRequest) -> None:
    is_email_exist = await AppCtx.current.db.session.scalar(
        sql_exp.exists().where(m.User.email == q.email).select()
    )

    if is_email_exist:
        raise fastapi_util.LogicError(
            code="already_exist_email",
            message="already exist email",
        )

    user = m.User(
        email=q.email,
        nickname=q.nickname,
        password=await auth_util.generate_hashed_password(
            q.password.get_secret_value()
        ),
    )

    AppCtx.current.db.session.add(user)

    try:
        await AppCtx.current.db.session.commit()
    except IntegrityError:
        raise fastapi_util.LogicError(
            code="try_again",
            message="there is a race condition. try again.",
        )


class _LoginRequest(BaseModel):
    email: EmailStr
    password: SecretStr


class _LoginResponse(BaseModel):
    access_token: str
    refresh_token: str


@router.post("/login")
async def login_api(q: _LoginRequest) -> _LoginResponse:
    user: m.User | None = (
        await AppCtx.current.db.session.execute(
            sql_exp.select(m.User).where(m.User.email == q.email)
        )
    ).scalar_one_or_none()

    if user is None:
        raise fastapi_util.LogicError(
            code="not_found_user",
            message="failed to found user by this email",
        )

    if not auth_util.validate_hashed_password(
        q.password.get_secret_value(),
        user.password,  # type: ignore
    ):
        raise fastapi_util.LogicError(
            code="invalid_password", message="this password is not valid"
        )

    access_token, refresh_token = await auth_util.generate_token(
        user.id  # type: ignore
    )

    return _LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/login/oauth")
async def login_oauth_api(q: OAuth2PasswordRequestForm = Depends()) -> _LoginResponse:
    user: m.User | None = (
        await AppCtx.current.db.session.execute(
            sql_exp.select(m.User).where(m.User.email == q.username)
        )
    ).scalar_one_or_none()

    if user is None:
        raise fastapi_util.LogicError(
            code="not_found_user",
            message="failed to found user by this email",
        )

    if not auth_util.validate_hashed_password(
        q.password,
        user.password,  # type: ignore
    ):
        raise fastapi_util.LogicError(
            code="invalid_password", message="this password is not valid"
        )

    access_token, refresh_token = await auth_util.generate_token(
        user.id  # type: ignore
    )

    return _LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


class _SocialSignUpRequest(BaseModel):
    code: str
    redirect_uri: str
    provider_type: oauth_util.ProviderTypeEnum


class _SocialSignUpResponse(BaseModel):
    access_token: str
    refresh_token: str
    social_access_token: str
    social_refresh_token: str


@router.post("/signup/social")
async def social_signup_api(q: _SocialSignUpRequest) -> _SocialSignUpResponse:
    try:
        (
            social_access_token,
            social_refresh_token,
        ) = await oauth_util.get_social_token(
            q.code,
            q.redirect_uri,
            q.provider_type,
        )
        social_info = await oauth_util.get_social_info(
            social_access_token, q.provider_type
        )
    except oauth_util.OauthUtilError as ex:
        raise fastapi_util.LogicError(
            code=ex.code,
            message=ex.message,
        )

    is_oauth_login_exists: bool = await AppCtx.current.db.session.scalar(
        sql_exp.exists()
        .where(
            (m.UserOauthLogin.uid == social_info.uid)
            & (m.UserOauthLogin.provider_type == q.provider_type)
        )
        .select()
    )

    if is_oauth_login_exists:
        raise fastapi_util.LogicError(
            code="already_exist_uid",
            message="Already signed up user",
        )

    user = m.User(
        email=social_info.email,
        nickname=social_info.name,
    )

    user_oauth_login = m.UserOauthLogin(
        user=user,
        uid=social_info.uid,
        provider_type=q.provider_type,
    )

    AppCtx.current.db.session.add(user)
    AppCtx.current.db.session.add(user_oauth_login)

    await AppCtx.current.db.session.commit()

    access_token, refresh_token = await auth_util.generate_token(
        user.id  # type: ignore
    )

    return _SocialSignUpResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        social_access_token=social_access_token,
        social_refresh_token=social_refresh_token,
    )


class _SocialLoginRequest(BaseModel):
    code: str
    redirect_uri: str
    provider_type: oauth_util.ProviderTypeEnum


class _SocialLoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    social_access_token: str
    social_refresh_token: str


@router.post("/login/social")
async def social_login_api(q: _SocialLoginRequest) -> _SocialLoginResponse:
    social_access_token, social_refresh_token = await oauth_util.get_social_token(
        q.code,
        q.redirect_uri,
        q.provider_type,
    )
    try:
        social_info = await oauth_util.get_social_info(
            social_access_token, q.provider_type
        )
    except oauth_util.OauthUtilError as ex:
        raise fastapi_util.LogicError(
            code=ex.code,
            message=ex.message,
            detail=ex.detail,
        )

    user: m.User | None = (
        await AppCtx.current.db.session.execute(
            sql_exp.select(m.User)
            .join(m.User.user_oauth_logins)
            .where(
                (m.UserOauthLogin.uid == social_info.uid)
                & (m.UserOauthLogin.provider_type == q.provider_type)
            )
        )
    ).scalar_one_or_none()

    if user is None:
        raise fastapi_util.LogicError(
            code="not_found_user",
            message="failed to found user by this email",
        )

    access_token, refresh_token = auth_util.generate_token(user.id)

    return _SocialLoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        social_access_token=social_access_token,
        social_refresh_token=social_refresh_token,
    )


class _AuthRefreshApiRequest(BaseModel):
    refresh_token: str


@router.post("/refresh")
async def refresh_api(q: _AuthRefreshApiRequest) -> _LoginResponse:
    try:
        token_info = jwt.decode(
            jwt=q.refresh_token,
            key=AppCtx.current.settings.SECRET_KEY,
            algorithms=["HS256"],
        )
    except jwt.ExpiredSignatureError:
        raise fastapi_util.AuthError(
            code="token_is_expired",
            message="refresh token is expired",
        )
    except jwt.DecodeError:
        raise fastapi_util.AuthError(
            code="token_decode_failure",
            message="failed to decode token",
        )

    user_id = token_info.get("user_id")
    if not isinstance(user_id, int):
        raise fastapi_util.AuthError(
            code="invalid_token_structure",
            message="token structure is invalid",
        )

    is_user_exist: bool = await AppCtx.current.db.session.scalar(
        sql_exp.exists().where(m.User.id == user_id).select()
    )
    if not is_user_exist:
        raise fastapi_util.AuthError(
            code="user_deleted",
            message="user is not exists",
        )

    access_token, refresh_token = auth_util.generate_token(user_id)

    return _LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


class _GuestLoginRequest(BaseModel):
    nickname: str
    is_agreed: bool


@router.post("/login/guest")
async def guest_login_api(q: _GuestLoginRequest) -> _LoginResponse:
    user = m.User(
        nickname=q.nickname,
        password=auth_util.generate_hashed_password(
            auth_util.generate_random_token(10)
        ),
    )

    AppCtx.current.db.session.add(user)
    await AppCtx.current.db.session.commit()

    access_token, refresh_token = auth_util.generate_token(user.id)

    return _LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )
