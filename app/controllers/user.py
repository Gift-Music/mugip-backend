from typing import Any, Dict, List, Literal, Optional

import jsonschema
import jsonschema.exceptions
import pydantic
from fastapi import Depends, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Query, Session
from sqlalchemy.sql import expression as sql_exp

import app.models.postgres as m
from app.utils.auth import user_auth_required
from app.utils.fastapi import CustomAPIRouter, NotFoundError, get_db_session
from app.utils.filter_expr import build_filter_expr

router = CustomAPIRouter(prefix='/user', tags=['user'])


class _UserPutRequest(BaseModel):
    nickname: str
    profile_image_url: Optional[str]


@router.put('/')
def user_put_me_api(
    q: _UserPutRequest,
    db_session: Session = Depends(get_db_session),
    me_user_id: int = Depends(user_auth_required),
) -> None:
    user = db_session \
        .query(m.UserModel) \
        .filter(m.UserModel.id == me_user_id) \
        .one()

    user.nickname = q.nickname

    if q.profile_image_url is not None:
        profile_image = m.UserProfileImageLogModel(
            user=user,
            profile_image_url=q.profile_image_url,
        )
        db_session.add(profile_image)

    db_session.commit()


class _UserGetResponse(BaseModel):
    id: int
    email: str
    nickname: str
    last_profile_image_url: str

    class Config:
        orm_mode = True


@router.get('/')
def user_get_me_api(
    db_session: Session = Depends(get_db_session),
    me_user_id: int = Depends(user_auth_required),
) -> _UserGetResponse:
    user = db_session \
        .query(m.UserModel) \
        .filter(m.UserModel.id == me_user_id) \
        .one()

    return _UserGetResponse.from_orm(user)


@router.get('/{user_id:int}')
def user_get_api(
    user_id: int,
    db_session: Session = Depends(get_db_session),
    me_user_id: int = Depends(user_auth_required),
) -> _UserGetResponse:
    user = db_session \
        .query(m.UserModel) \
        .filter(m.UserModel.id == user_id) \
        .one_or_none()

    if user is None:
        raise NotFoundError(
            code='not_found_user',
            message='failed to found user by this id',
        )

    return _UserGetResponse.from_orm(user)


_UserSearchRequestFilterExpr = build_filter_expr({
    'email': {'type': 'string'},
    'nickname': {'type': 'string'},
})


class _UserSearchRequest(BaseModel):
    filter_expr: Optional[Dict[str, Any]] = Field(description=_UserSearchRequestFilterExpr.description)
    sort_by_key: Optional[Literal['id', 'nickname', 'email', 'created', 'updated']]
    sort_by_order: Optional[Literal['asc', 'desc']]
    offset: int = Field(ge=0)
    count: int = Field(ge=1, le=100)

    @pydantic.validator('filter_expr')
    def validator_filter_expr(cls, value: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if value is not None:
            try:
                jsonschema.validate(
                    value,
                    _UserSearchRequestFilterExpr.schema,
                    format_checker=jsonschema.draft7_format_checker,
                )
            except jsonschema.exceptions.ValidationError as err:
                raise ValueError(err.message)
        return value


class _UserSearchResponse(BaseModel):
    id: int
    email: str
    nickname: str
    last_profile_image_url: str

    class Config:
        orm_mode = True


@router.post('/search')
def user_search_post_api(
    q: _UserSearchRequest,
    response: Response,
    db_session: Session = Depends(get_db_session),
    me_user_id: int = Depends(user_auth_required),
) -> List[_UserSearchResponse]:
    users_query = db_session \
        .query(m.UserModel)

    if q.filter_expr is not None:
        users_query = users_query \
            .filter(
                _UserSearchRequestFilterExpr.to_query(
                    q.filter_expr,
                    {
                        'email': m.UserModel.email.ilike,
                        'nickname': m.UserModel.nickname.ilike,
                    }
                )
            )

    sort_by_col = {
        'id': m.UserModel.id,
        'nickname': m.UserModel.nickname,
        'email': m.UserModel.email,
        'created': m.UserModel.created,
        'updated': m.UserModel.updated,
    }[q.sort_by_key or 'id']

    sort_by_order_exp = {
        'asc': sql_exp.asc,
        'desc': sql_exp.desc,
    }[q.sort_by_order or 'asc']

    users_count = users_query.count()
    response.headers['x-total'] = str(users_count)

    users = users_query \
        .order_by(sort_by_order_exp(sort_by_col)) \
        .slice(q.offset, q.offset + q.count) \
        .all()

    return [
        _UserSearchResponse.from_orm(user)
        for user in users
    ]


@router.get('/followers')
def user_followers_get_api(
    response: Response,
    offset: int = 0,
    count: int = 100,
    db_session: Session = Depends(get_db_session),
    me_user_id: int = Depends(user_auth_required),
) -> List[_UserSearchResponse]:
    followers_query: Query[m.UserModel] = db_session \
        .query(m.UserModel) \
        .join(m.UserModel.followers) \
        .filter(m.UserFollowRelation.target_user_id == me_user_id)

    followers_count = followers_query.count()
    response.headers['x-total'] = str(followers_count)

    followers = followers_query \
        .offset(offset) \
        .limit(count) \
        .all()

    return [
        _UserSearchResponse.from_orm(user)
        for user in followers
    ]


@router.get('/followings')
def user_followings_get_api(
    response: Response,
    offset: int = 0,
    count: int = 100,
    db_session: Session = Depends(get_db_session),
    me_user_id: int = Depends(user_auth_required),
) -> List[_UserSearchResponse]:
    followings_query: Query[m.UserModel] = db_session \
        .query(m.UserModel) \
        .join(m.UserModel.followings) \
        .filter(m.UserFollowRelation.request_user_id == me_user_id)

    followings_count = followings_query.count()
    response.headers['x-total'] = str(followings_count)

    followings = followings_query \
        .offset(offset) \
        .limit(count) \
        .all()

    return [
        _UserSearchResponse.from_orm(user)
        for user in followings
    ]


class _UserFollowPostRequset(BaseModel):
    target_user_id: int


@router.post('/follow')
def follow_post_api(
    q: _UserFollowPostRequset,
    db_session: Session = Depends(get_db_session),
    me_user_id: int = Depends(user_auth_required),
) -> None:
    is_target_user_exist: bool = db_session \
        .query(
            sql_exp
            .exists()
            .where(m.UserModel.id == q.target_user_id)
        ) \
        .scalar()

    if not is_target_user_exist:
        raise NotFoundError(
            code='not_found_user',
            message='failed to found user by this id',
        )

    db_session.add(
        m.UserFollowRelation(
            request_user_id=me_user_id,
            target_user_id=q.target_user_id,
        )
    )

    db_session.commit()
