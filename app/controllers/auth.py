from fastapi import Depends
from pydantic import BaseModel, EmailStr, Field, SecretStr
from redis import Redis
from sqlalchemy.orm import Session
from sqlalchemy.sql import expression as sql_exp

from app import models as m
from app.utils import auth as auth_utils
from app.utils import server as server_utils
from app.utils.misc import generate_hashed_password, get_db_session, get_redis, validate_hashed_password

router = server_utils.CustomAPIRouter(prefix='/auth', tags=['auth'])


class _AuthSignupRequestBase(BaseModel):
    email: EmailStr = Field(description='이메일')


class _AuthSignupRequest(_AuthSignupRequestBase):
    password: SecretStr = Field(description='로그인 PW', min_length=8)


class _AuthSignupResponse(BaseModel):
    user_id: int


@router.post('/signup')
def auth_signup_api(
    q: _AuthSignupRequest,
    db_session: Session = Depends(get_db_session),
) -> _AuthSignupResponse:
    return _signup_api(q, db_session)


class _AuthSignupOauthRequest(_AuthSignupRequestBase):
    oauth_uid: str
    provider_type: m.UserOauthProviderTypeEnum


@router.post('/signup/oauth')
def auth_signup_oauth_api(
    q: _AuthSignupOauthRequest,
    db_session: Session = Depends(get_db_session),
) -> _AuthSignupResponse:
    return _signup_api(q, db_session)


def _signup_api(
    q: _AuthSignupRequestBase,
    db_session: Session,
) -> _AuthSignupResponse:
    is_email_exist: bool = db_session \
        .scalar(
            sql_exp
            .exists()
            .where(m.UserModel.email == q.email)
            .select()
        )

    if is_email_exist:
        raise server_utils.LogicError(
            code='email_conflict',
            message='already signed up email',
        )

    user = m.UserModel(email=q.email)
    db_session.add(user)

    if isinstance(q, _AuthSignupRequest):
        user.password = generate_hashed_password(q.password.get_secret_value())

    elif isinstance(q, _AuthSignupOauthRequest):
        db_session.flush()
        oauth_login = m.UserOauthLoginRelation(
            user=user,
            uid=q.oauth_uid,
            provider_type=q.provider_type,
        )
        db_session.add(oauth_login)

    db_session.commit()

    return _AuthSignupResponse(user_id=user.id)


class _AuthLoginRequest(BaseModel):
    email: str = Field(description='이메일')
    password: SecretStr = Field(description='로그인 PW', min_length=8)


class _AuthLoginResponse(BaseModel):
    access_token: str
    refresh_token: str


@router.post('/login')
def auth_login_api(
    q: _AuthLoginRequest,
    db_session: Session = Depends(get_db_session),
    redis: Redis = Depends(get_redis)
) -> _AuthLoginResponse:
    user = db_session \
        .query(m.UserModel) \
        .filter(m.UserModel.email == q.email) \
        .one_or_none()

    if user is None:
        raise server_utils.LogicError(
            code='not_found',
            message='the email is not signed up in server',
        )

    if user.password is None:
        raise server_utils.LogicError(
            code='no_password',
            message='the user is not signed up by password',
        )

    if not validate_hashed_password(q.password.get_secret_value(), user.password):
        raise server_utils.LogicError(
            code='password_not_valid',
            message='password is not valid',
        )

    auth_utils.login_user(user.id, redis)
    access_token, refresh_token = auth_utils.generate_tokens(user.id)

    return _AuthLoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )
