import jwt
import sqlalchemy
from fastapi import Depends
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, SecretStr
from sqlalchemy.orm import Session
from sqlalchemy.sql import expression as sql_exp

from app.models import postgres as m
from app.settings import AppSettings
from app.utils import AppUtils
from app.utils import auth as auth_util
from app.utils import email as email_util
from app.utils import fastapi as fastapi_util
from app.utils import oauth as oauth_util
from app.utils.fastapi import (CustomAPIRouter, get_app_settings, get_app_utils,
                               get_db_session)

router = CustomAPIRouter(prefix="/auth", tags=["auth"])


class _SignUpRequest(BaseModel):
    email: EmailStr
    nickname: str
    password: SecretStr
    is_agreed: bool


@router.post("/signup")
def signup_api(
    q: _SignUpRequest,
    app_utils: AppUtils = Depends(get_app_utils),
    db_session: Session = Depends(get_db_session),
) -> None:
    is_email_exist = db_session.scalar(
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
        password=auth_util.generate_hashed_password(q.password.get_secret_value()),
    )

    db_session.add(user)

    try:
        db_session.flush()
    except sqlalchemy.exc.IntegrityError:
        raise fastapi_util.LogicError(
            code="try_again",
            message="there is a race condition. try again.",
        )

    verify_token = app_utils.auth.issue_verify_token(q.email)

    app_utils.email.send_email(
        email_util.EmailModel(
            to=q.email,
            subject="Mugip 인증",
            message=f"인증번호: {verify_token}",
        )
    )

    db_session.commit()


class _VerifyEmailRequest(BaseModel):
    email: EmailStr
    token: str


class _VerifyEmailResponse(BaseModel):
    access_token: str
    refresh_token: str


@router.post("/verify/email")
def verify_token_api(
    q: _VerifyEmailRequest,
    app_utils: AppUtils = Depends(get_app_utils),
    db_session: Session = Depends(get_db_session),
) -> _VerifyEmailResponse:
    email = app_utils.auth.get_verify_token(q.token)

    if email != q.email:
        raise fastapi_util.LogicError(
            code="invalid_token", message="this token is not valid"
        )

    app_utils.auth.delete_verify_token(q.token)

    user = db_session.query(m.User).filter(m.User.email == q.email).one_or_none()

    if user is None:
        raise fastapi_util.LogicError(
            code="not_found_user",
            message="failed to found user by this email",
        )

    access_token, refresh_token = app_utils.auth.generate_token(user.id)

    return _VerifyEmailResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


class _LoginRequest(BaseModel):
    email: EmailStr
    password: SecretStr


class _LoginResponse(BaseModel):
    access_token: str
    refresh_token: str


@router.post("/login")
def login_api(
    q: _LoginRequest,
    app_utils: AppUtils = Depends(get_app_utils),
    db_session: Session = Depends(get_db_session),
) -> _LoginResponse:
    user = db_session.query(m.User).filter(m.User.email == q.email).one_or_none()

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

    access_token, refresh_token = app_utils.auth.generate_token(user.id)

    return _LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/login/oauth")
def login_oauth_api(
    q: OAuth2PasswordRequestForm = Depends(),
    app_utils: AppUtils = Depends(get_app_utils),
    db_session: Session = Depends(get_db_session),
) -> _LoginResponse:
    user = db_session.query(m.User).filter(m.User.email == q.username).one_or_none()

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

    access_token, refresh_token = app_utils.auth.generate_token(user.id)

    return _LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


class _SocialSignUpRequest(BaseModel):
    code: str
    redirect_uri: str
    provider_type: int


class _SocialSignUpResponse(BaseModel):
    access_token: str
    refresh_token: str
    social_access_token: str
    social_refresh_token: str


@router.post("/signup/social")
async def social_signup_api(
    q: _SocialSignUpRequest,
    app_utils: AppUtils = Depends(get_app_utils),
    db_session: Session = Depends(get_db_session),
) -> _SocialSignUpResponse:
    try:
        (
            social_access_token,
            social_refresh_token,
        ) = await app_utils.social.get_social_token(
            q.code,
            q.redirect_uri,
            q.provider_type,
        )
        social_info = await app_utils.social.get_social_info(
            social_access_token, q.provider_type
        )
    except oauth_util.OauthUtilError as ex:
        raise fastapi_util.LogicError(
            code=ex.code,
            message=ex.message,
        )

    is_oauth_login_exists: bool = db_session.scalar(
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

    db_session.add(user)
    db_session.add(user_oauth_login)

    db_session.commit()

    access_token, refresh_token = app_utils.auth.generate_token(user.id)

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
async def social_login_api(
    q: _SocialLoginRequest,
    app_utils: AppUtils = Depends(get_app_utils),
    db_session: Session = Depends(get_db_session),
) -> _SocialLoginResponse:
    social_access_token, social_refresh_token = await app_utils.social.get_social_token(
        q.code,
        q.redirect_uri,
        q.provider_type,
    )
    try:
        social_info = await app_utils.social.get_social_info(
            social_access_token, q.provider_type
        )
    except oauth_util.OauthUtilError as ex:
        raise fastapi_util.LogicError(
            code=ex.code,
            message=ex.message,
            detail=ex.detail,
        )

    user = (
        db_session.query(m.User)
        .join(m.User.user_oauth_logins)
        .filter(
            (m.UserOauthLogin.uid == social_info.uid)
            & (m.UserOauthLogin.provider_type == q.provider_type)
        )
        .one_or_none()
    )

    if user is None:
        raise fastapi_util.LogicError(
            code="not_found_user",
            message="failed to found user by this email",
        )

    access_token, refresh_token = app_utils.auth.generate_token(user.id)

    return _SocialLoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        social_access_token=social_access_token,
        social_refresh_token=social_refresh_token,
    )


class _AuthRefreshApiRequest(BaseModel):
    refresh_token: str


@router.post("/refresh")
def refresh_api(
    q: _AuthRefreshApiRequest,
    app_utils: AppUtils = Depends(get_app_utils),
    app_settings: AppSettings = Depends(get_app_settings),
    db_session: Session = Depends(get_db_session),
) -> _LoginResponse:
    try:
        token_info = jwt.decode(
            jwt=q.refresh_token,
            key=app_settings.SECRET_KEY,
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

    is_user_exist: bool = db_session.scalar(
        sql_exp.exists().where(m.User.id == user_id).select()
    )
    if not is_user_exist:
        raise fastapi_util.AuthError(
            code="user_deleted",
            message="user is not exists",
        )

    access_token, refresh_token = app_utils.auth.generate_token(user_id)

    return _LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


class _GuestLoginRequest(BaseModel):
    nickname: str
    is_agreed: bool


@router.post("/login/guest")
def guest_login_api(
    q: _GuestLoginRequest,
    app_utils: AppUtils = Depends(get_app_utils),
    db_session: Session = Depends(get_db_session),
) -> _LoginResponse:
    user = m.User(
        nickname=q.nickname,
        password=auth_util.generate_hashed_password(
            auth_util.generate_random_token(10)
        ),
    )

    db_session.add(user)
    db_session.commit()

    access_token, refresh_token = app_utils.auth.generate_token(user.id)

    return _LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )
