import sqlalchemy
from fastapi import Depends
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, SecretStr
from sqlalchemy.orm import Session
from sqlalchemy.sql import expression as sql_exp

from app.models import postgres as m
from app.utils import AppUtils
from app.utils import auth as auth_util
from app.utils import email as email_util
from app.utils import fastapi as fastapi_util
from app.utils import oauth as oauth_util
from app.utils.fastapi import CustomAPIRouter, get_app_utils, get_db_session

router = CustomAPIRouter(prefix='/auth', tags=['auth'])


class _SignUpRequest(BaseModel):
    email: EmailStr
    nickname: str
    password: SecretStr
    is_agreed: bool


@router.post('/signup')
def signup_api(
    q: _SignUpRequest,
    app_utils: AppUtils = Depends(get_app_utils),
    db_session: Session = Depends(get_db_session),
) -> None:
    is_email_exist = db_session \
        .scalar(
            sql_exp
            .exists()
            .where(m.UserModel.email == q.email)
            .select()
        )

    if is_email_exist:
        raise fastapi_util.LogicError(
            code='already_exist_email',
            message='already exist email',
        )

    user = m.UserModel(
        email=q.email,
        nickname=q.nickname,
        password=auth_util.generate_hashed_password(q.password.get_secret_value()),
    )

    db_session.add(user)

    try:
        db_session.flush()
    except sqlalchemy.exc.IntegrityError:
        raise fastapi_util.LogicError(
            code='try_again',
            message='there is a race condition. try again.',
        )

    verify_token = app_utils.auth.issue_verify_token(q.email)

    app_utils.email.send_email(
        email_util.EmailModel(
            to=q.email,
            subject='Mugip 인증',
            message=f'인증번호: {verify_token}',
        )
    )

    db_session.commit()


class _VerifyEmailRequest(BaseModel):
    email: EmailStr
    token: str


class _VerifyEmailResponse(BaseModel):
    access_token: str
    refresh_token: str


@router.post('/verify/email')
def verify_token_api(
    q: _VerifyEmailRequest,
    app_utils: AppUtils = Depends(get_app_utils),
    db_session: Session = Depends(get_db_session),
) -> _VerifyEmailResponse:
    email = app_utils.auth.get_verify_token(q.token)

    if email != q.email:
        raise fastapi_util.LogicError(
            code='invalid_token',
            message='this token is not valid'
        )

    app_utils.auth.delete_verify_token(q.token)

    user = db_session \
        .query(m.UserModel) \
        .filter(m.UserModel.email == q.email) \
        .one_or_none()

    if user is None:
        raise fastapi_util.NotFoundError(
            code='not_found_user',
            message='failed to found user by this email',
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


@router.post('/login')
def login_api(
    q: _LoginRequest,
    app_utils: AppUtils = Depends(get_app_utils),
    db_session: Session = Depends(get_db_session),
) -> _LoginResponse:
    user = db_session \
        .query(m.UserModel) \
        .filter(m.UserModel.email == q.email) \
        .one_or_none()

    if user is None:
        raise fastapi_util.NotFoundError(
            code='not_found_user',
            message='failed to found user by this email',
        )

    if not auth_util.validate_hashed_password(q.password.get_secret_value(), user.password):
        raise fastapi_util.LogicError(
            code='invalid_password',
            message='this password is not valid'
        )

    access_token, refresh_token = app_utils.auth.generate_token(user.id)

    return _LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post('/login/oauth')
def login_oauth_api(
    q: OAuth2PasswordRequestForm = Depends(),
    app_utils: AppUtils = Depends(get_app_utils),
    db_session: Session = Depends(get_db_session),
) -> _LoginResponse:
    user = db_session \
        .query(m.UserModel) \
        .filter(m.UserModel.email == q.username) \
        .one_or_none()

    if user is None:
        raise fastapi_util.NotFoundError(
            code='not_found_user',
            message='failed to found user by this email',
        )

    if not auth_util.validate_hashed_password(q.password, user.password):
        raise fastapi_util.LogicError(
            code='invalid_password',
            message='this password is not valid'
        )

    access_token, refresh_token = app_utils.auth.generate_token(user.id)

    return _LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


class _SocialSignUpRequest(BaseModel):
    email: EmailStr
    token: str
    provider_type: oauth_util.ProviderTypeEnum


class _SocialSignUpResponse(BaseModel):
    access_token: str
    refresh_token: str


@router.post('/signup/social')
def oauth_signup_api(
    q: _SocialSignUpRequest,
    app_utils: AppUtils = Depends(get_app_utils),
    db_session: Session = Depends(get_db_session),
) -> _SocialSignUpResponse:
    is_email_exist = db_session \
        .scalar(
            sql_exp
            .exists()
            .where(m.UserModel.email == q.email)
            .select()
        )

    if is_email_exist:
        raise fastapi_util.LogicError(
            code='already_exist_email',
            message='already exist email',
        )

    social_uid = oauth_util.get_social_uid_by_token_n_provider_type(q.token, q.provider_type)

    user = m.UserModel(email=q.email)

    user_oauth_login = m.UserOauthLoginRelation(
        user=user,
        uid=social_uid,
        provider_type=q.provider_type,
    )

    db_session.add(user)
    db_session.add(user_oauth_login)

    db_session.commit()

    access_token, refresh_token = app_utils.auth.generate_token(user.id)

    return _SocialSignUpResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


class _SocialLoginRequest(BaseModel):
    email: EmailStr
    token: str
    provider_type: oauth_util.ProviderTypeEnum


@router.post('/login/social')
def oauth_login_api(
    q: _SocialLoginRequest,
    app_utils: AppUtils = Depends(get_app_utils),
    db_session: Session = Depends(get_db_session),
) -> _LoginResponse:
    social_uid = oauth_util.get_social_uid_by_token_n_provider_type(q.token, q.provider_type)

    user = db_session \
        .query(m.UserOauthLoginRelation.user) \
        .join(m.UserOauthLoginRelation.user) \
        .filter(
            (m.UserOauthLoginRelation.uid == social_uid)
            & (m.UserOauthLoginRelation.provider_type == q.provider_type)
        ) \
        .one_or_none()

    if user is None:
        raise fastapi_util.NotFoundError(
            code='not_found_user',
            message='failed to found user by this email',
        )

    access_token, refresh_token = app_utils.auth.generate_token(user.id)

    return _LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )
