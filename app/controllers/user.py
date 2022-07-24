import io
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

import jsonschema
import jsonschema.exceptions
import pydantic
from fastapi import Depends, File, Response, UploadFile
from PIL import Image
from pydantic import BaseModel, Field
from sqlalchemy.orm import Query, Session
from sqlalchemy.sql import expression as sql_exp

import app.models.postgres as m
from app.utils import AppUtils
from app.utils.auth import user_auth_required
from app.utils.fastapi import (AppCtx.current.db.session, CustomAPIRouter, LogicError,
                               get_app_utils, get_await)
from app.utils.filter_expr import build_filter_expr

router = CustomAPIRouter(prefix="/user", tags=["user"])


class _UserPutRequest(BaseModel):
    nickname: str
    profile_image_url: Optional[str]


@router.put("/")
async def user_put_me_api(
    q: _UserPutRequest,
    await AppCtx.current.db.session: Session = Depends(get_await AppCtx.current.db.session),
    me_user_id: int = Depends(user_auth_required),
) -> None:
    user = await AppCtx.current.db.session.query(m.User).filter(m.User.id == me_user_id).one()

    user.nickname = q.nickname

    if q.profile_image_url is not None:
        profile_image = m.UserProfileImageLog(
            user=user,
            profile_image_url=q.profile_image_url,
        )
        AppCtx.current.db.session.add(profile_image)

    await AppCtx.current.db.session.commit()


class _UserGetResponse(BaseModel):
    id: int
    email: str
    nickname: str
    last_profile_image_url: str

    class Config:
        orm_mode = True


@router.get("/")
async def user_get_me_api(
    await AppCtx.current.db.session: Session = Depends(get_await AppCtx.current.db.session),
    me_user_id: int = Depends(user_auth_required),
) -> _UserGetResponse:
    user = await AppCtx.current.db.session.query(m.User).filter(m.User.id == me_user_id).one()

    return _UserGetResponse.from_orm(user)


@router.get("/{user_id:int}")
async def user_get_api(
    user_id: int,
    await AppCtx.current.db.session: Session = Depends(get_await AppCtx.current.db.session),
    me_user_id: int = Depends(user_auth_required),
) -> _UserGetResponse:
    user = await AppCtx.current.db.session.query(m.User).filter(m.User.id == user_id).one_or_none()

    if user is None:
        raise LogicError(
            code="not_found_user",
            message="failed to found user by this id",
        )

    return _UserGetResponse.from_orm(user)


@router.post("/profile_image")
async def user_profile_image_post_api(
    profile_file: UploadFile = File(),
    await AppCtx.current.db.session: Session = Depends(get_await AppCtx.current.db.session),
    me_user_id: int = Depends(user_auth_required),
    app_utils: AppUtils = Depends(get_app_utils),
) -> None:
    current_dt = datetime.now().isoformat()

    user = await AppCtx.current.db.session.query(m.User).filter(m.User.id == me_user_id).one_or_none()

    if user is None:
        raise LogicError(
            code="not_found_user",
            message="failed to found user by this id",
        )

    try:
        with (
            Image.open(profile_file.file) as profile_image,
            io.BytesIO() as f,
        ):
            # TODO : make the size of thumbnail configuable in config.py
            profile_image = profile_image.convert("RGBA")
            profile_image.thumbnail((300, 300))
            new_profile_image = Image.new("RGB", profile_image.size, (255, 255, 255))

            # Only non-transparent areas are pasted (box argument)
            new_profile_image.paste(profile_image, box=profile_image)
            new_profile_image.save(f, "JPEG")

            f.seek(0)

            file_name = f"{me_user_id}_{current_dt}_{profile_file.filename}"
            profile_image_url = app_utils.remote_file.upload_profile_image(
                file_name,
                f,
            )

    except RuntimeError as ex:
        raise LogicError(
            code="profile_file_upload_error",
            message=ex.msg,
            detail={"aws_error": ex.detail},
        )
    except Exception as ex:
        raise LogicError(
            code="cannot_open_profile",
            message="you cannot open profile image",
            detail={"ex": str(ex)},
        )

    AppCtx.current.db.session.add(
        m.UserProfileImageLog(
            profile_image_url=profile_image_url,
            user=user,
        )
    )

    await AppCtx.current.db.session.commit()


_UserSearchRequestFilterExpr = build_filter_expr(
    {
        "email": {"type": "string"},
        "nickname": {"type": "string"},
    }
)


class _UserSearchRequest(BaseModel):
    filter_expr: Optional[Dict[str, Any]] = Field(
        description=_UserSearchRequestFilterExpr.description
    )
    sort_by_key: Optional[Literal["id", "nickname", "email", "created", "updated"]]
    sort_by_order: Optional[Literal["asc", "desc"]]
    offset: int = Field(ge=0)
    count: int = Field(ge=1, le=100)

    @pydantic.validator("filter_expr")
    def validator_filter_expr(
        cls, value: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
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


@router.post("/search")
async def user_search_post_api(
    q: _UserSearchRequest,
    response: Response,
    await AppCtx.current.db.session: Session = Depends(get_await AppCtx.current.db.session),
    me_user_id: int = Depends(user_auth_required),
) -> List[_UserSearchResponse]:
    users_query = await AppCtx.current.db.session.query(m.User)

    if q.filter_expr is not None:
        users_query = users_query.filter(
            _UserSearchRequestFilterExpr.to_query(
                q.filter_expr,
                {
                    "email": m.User.email.ilike,
                    "nickname": m.User.nickname.ilike,
                },
            )
        )

    sort_by_col = {
        "id": m.User.id,
        "nickname": m.User.nickname,
        "email": m.User.email,
        "created": m.User.created,
        "updated": m.User.updated,
    }[q.sort_by_key or "id"]

    sort_by_order_exp = {
        "asc": sql_exp.asc,
        "desc": sql_exp.desc,
    }[q.sort_by_order or "asc"]

    users_count = users_query.count()
    response.headers["x-total"] = str(users_count)

    users = (
        users_query.order_by(sort_by_order_exp(sort_by_col))
        .slice(q.offset, q.offset + q.count)
        .all()
    )

    return [_UserSearchResponse.from_orm(user) for user in users]


@router.get("/followers")
async def user_followers_get_api(
    response: Response,
    offset: int = 0,
    count: int = 100,
    await AppCtx.current.db.session: Session = Depends(get_await AppCtx.current.db.session),
    me_user_id: int = Depends(user_auth_required),
) -> List[_UserSearchResponse]:
    followers_query: Query[m.User] = (
        await AppCtx.current.db.session.query(m.User)
        .join(m.UserFollow, (m.User.id == m.UserFollow.request_user_id))
        .filter(m.UserFollow.target_user_id == me_user_id)
    )

    followers_count = followers_query.count()
    response.headers["x-total"] = str(followers_count)

    followers = followers_query.offset(offset).limit(count).all()

    return [_UserSearchResponse.from_orm(user) for user in followers]


@router.get("/followings")
async def user_followings_get_api(
    response: Response,
    offset: int = 0,
    count: int = 100,
    await AppCtx.current.db.session: Session = Depends(get_await AppCtx.current.db.session),
    me_user_id: int = Depends(user_auth_required),
) -> List[_UserSearchResponse]:
    followings_query: Query[m.User] = (
        await AppCtx.current.db.session.query(m.User)
        .join(
            m.UserFollow,
            (m.User.id == m.UserFollow.target_user_id),
        )
        .filter(m.UserFollow.request_user_id == me_user_id)
    )

    followings_count = followings_query.count()
    response.headers["x-total"] = str(followings_count)

    followings = followings_query.offset(offset).limit(count).all()

    return [_UserSearchResponse.from_orm(user) for user in followings]


class _UserFollowPostRequset(BaseModel):
    target_user_id: int


@router.post("/follow")
def follow_post_api(
    q: _UserFollowPostRequset,
    await AppCtx.current.db.session: Session = Depends(get_await AppCtx.current.db.session),
    me_user_id: int = Depends(user_auth_required),
) -> None:
    is_target_user_exist: bool = await AppCtx.current.db.session.scalar(
        sql_exp.exists().where(m.User.id == q.target_user_id).select()
    )

    if not is_target_user_exist:
        raise LogicError(
            code="not_found_user",
            message="failed to found user by this id",
        )

    AppCtx.current.db.session.add(
        m.UserFollow(
            request_user_id=me_user_id,
            target_user_id=q.target_user_id,
        )
    )

    await AppCtx.current.db.session.commit()


@router.delete("/")
def delete_all(
    await AppCtx.current.db.session: Session = Depends(get_await AppCtx.current.db.session),
) -> None:
    await AppCtx.current.db.session.query(m.User).delete()

    await AppCtx.current.db.session.commit()
