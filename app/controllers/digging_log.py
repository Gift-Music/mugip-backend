from __future__ import annotations

import datetime
from typing import Any, Dict, List, Literal, Optional, Tuple

import jsonschema
from fastapi import Depends, Response
from geoalchemy2 import WKTElement
from pydantic import BaseModel, Field, validator
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import contains_eager, joinedload
from sqlalchemy.sql import expression as sql_exp
from sqlalchemy.sql import func as sql_func

from app.constants import DEFAULT_SRID
from app.ctx import AppCtx
from app.models import postgres as m
from app.utils import fastapi as fastapi_util
from app.utils import spotify as spotify_util
from app.utils.auth import user_auth_required
from app.utils.filter_expr import build_filter_expr

router = fastapi_util.CustomAPIRouter(prefix="/digging_log", tags=["digging_log"])


class _DiggingLogPostRequest(BaseModel):
    track_id: str
    tag_name: str
    coordinates: Tuple[float, float]


@router.post("/")
async def digging_log_post_api(
    q: _DiggingLogPostRequest,
    me_user_id: int = Depends(user_auth_required),
) -> None:
    track: m.Track = (
        await AppCtx.current.db.session.execute(
            sql_exp.select(m.Track).where(m.Track.id == q.track_id)
        )
    ).scalar_one_or_none()

    if track is None:
        track_obj = await spotify_util.get_track(q.track_id)
        album: m.Album = (
            await AppCtx.current.db.session.execute(
                sql_exp.select(m.Album).where(m.Album.id == track_obj.album.id)
            )
        ).scalar_one_or_none()

        if album is None:
            album = m.Album(
                id=track_obj.album.id,
                name=track_obj.album.name,
                release_date=track_obj.album.release_date,
                total_tracks=track_obj.album.total_tracks,
            )

        images = [
            m.Image(
                album=album,
                width=image.width,
                height=image.height,
                url=image.url,
            )
            for image in track_obj.album.images
        ]

        AppCtx.current.db.session.add(album)
        await AppCtx.current.db.session.add_all(images)

        await AppCtx.current.db.session.execute(
            pg_insert(m.Artist.__table__)
            .values(
                [
                    {
                        "id": artist.id,
                        "name": artist.name,
                    }
                    for artist in track_obj.artists
                ]
            )
            .on_conflict_do_nothing(constraint=m.Artist.__table__.primary_key)
        )
        track = m.Track(
            album=album,
            id=track_obj.id,
            duration_ms=track_obj.duration_ms,
            track_number=track_obj.track_number,
            preview_url=track_obj.preview_url,
        )
        artist_tracks = [
            m.ArtistTrack(
                artist_id=artist.id,
                track=track,
            )
            for artist in track_obj.artists
        ]
        AppCtx.current.db.session.add(track)
        await AppCtx.current.db.session.add_all(artist_tracks)

    tag: m.Tag = (
        await AppCtx.current.db.session.execute(
            sql_exp.select(m.Tag).where(m.Tag.name == q.tag_name)
        )
    ).scalar_one_or_none()

    if tag is None:
        raise fastapi_util.LogicError(
            code="not_found_tag",
            message="failed to found tag by this name",
        )

    user: m.User = (
        await AppCtx.current.db.session.execute(
            sql_exp.select(m.User).where(m.User.id == me_user_id)
        )
    ).scalar_one_or_none()

    if user is None:
        raise fastapi_util.LogicError(
            code="not_found_user",
            message="failed to found user by this id",
        )

    coordinates = WKTElement(
        f"POINT ({q.coordinates[0]} {q.coordinates[1]})", srid=DEFAULT_SRID
    )

    digging_log = m.DiggingLog(
        user=user,
        track=track,
        coordinates=coordinates,
    )

    AppCtx.current.db.session.add(digging_log)

    AppCtx.current.db.session.add(
        m.DiggingLogTag(
            digging_log=digging_log,
            tag=tag,
        )
    )

    await AppCtx.current.db.session.commit()


_DiggingLogSearchRequestFilterExpr = build_filter_expr(
    {
        "user_id": {"type": "integer"},
        "track_id": {"type": "string"},
        "tag_name": {"type": "string"},
    }
)


class _DiggingLogSearchRequest(BaseModel):
    filter_expr: Optional[Dict[str, Any]] = Field(
        description=_DiggingLogSearchRequestFilterExpr.description
    )
    sort_by_key: Optional[Literal["created", "updated"]]
    sort_by_order: Optional[Literal["asc", "desc"]]
    offset: int = Field(ge=0)
    count: int = Field(ge=1, le=100)

    @validator("filter_expr")
    def validator_filter_expr(
        cls, value: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        if value is not None:
            try:
                jsonschema.validate(
                    value,
                    _DiggingLogSearchRequestFilterExpr.schema,
                    format_checker=jsonschema.draft7_format_checker,
                )
            except jsonschema.ValidationError as err:
                raise ValueError(err.message)
        return value


class _DiggingLogSearchResponse(BaseModel):
    class Image(BaseModel):
        height: int
        url: str
        width: int

        class Config:
            orm_mode = True

    class Artist(BaseModel):
        id: str
        name: str

    class Album(BaseModel):
        id: str
        name: str
        release_date: datetime.datetime
        total_tracks: int
        images: List[_DiggingLogSearchResponse.Image]

        class Config:
            orm_mode = True

    class Track(BaseModel):
        id: str
        album: _DiggingLogSearchResponse.Album
        artists: List[_DiggingLogSearchResponse.Artist]
        duration_ms: int
        track_number: int
        preview_url: Optional[str]

        class Config:
            orm_mode = True

    class User(BaseModel):
        id: int
        nickname: Optional[str]
        email: Optional[str]
        last_profile_image_url: Optional[str]

        class Config:
            orm_mode = True

    class Tag(BaseModel):
        name: str
        icon: str

    track: _DiggingLogSearchResponse.Track
    user: _DiggingLogSearchResponse.User
    tags: List[_DiggingLogSearchResponse.Tag]

    class Config:
        orm_mode = True


_DiggingLogSearchResponse.update_forward_refs()
_DiggingLogSearchResponse.Track.update_forward_refs()
_DiggingLogSearchResponse.Album.update_forward_refs()
_DiggingLogSearchResponse.Artist.update_forward_refs()


@router.post("/search")
async def digging_log_search_api(
    q: _DiggingLogSearchRequest,
    response: Response,
    me_user_id: int = Depends(user_auth_required),
) -> List[_DiggingLogSearchResponse]:
    digging_logs_query: m.DiggingLog = await AppCtx.current.db.session.execute(
        sql_exp.select(m.DiggingLog)
        .join(m.DiggingLog.digging_log_tags)
        .options(
            contains_eager(m.DiggingLog.digging_log_tags),
            joinedload(m.DiggingLog.track),
        )
    )

    if q.filter_expr is not None:
        digging_logs_query = digging_logs_query.where(
            _DiggingLogSearchRequestFilterExpr.to_query(
                q.filter_expr,
                {
                    "user_id": m.DiggingLog.user_id.__eq__,
                    "track_id": m.DiggingLog.track_id.__eq__,
                    "tag_name": m.Tag.name.ilike,
                },
            )
        )

    sort_by_col = {
        "created": m.Tag.created,
        "updated": m.Tag.updated,
    }[q.sort_by_key or "id"]

    sort_by_order_exp = {
        "asc": sql_exp.asc,
        "desc": sql_exp.desc,
    }[q.sort_by_order or "asc"]

    digging_logs_count = await AppCtx.current.db.session.scalar(
        sql_func.count(digging_logs_query)
    )
    response.headers["x-total"] = str(digging_logs_count)

    digging_logs: list[m.DiggingLog] = (
        (
            await AppCtx.current.db.session.execute(
                digging_logs_query.order_by(sort_by_order_exp(sort_by_col)).slice(
                    q.offset, q.offset + q.count
                )
            )
        )
        .scalars()
        .all()
    )

    return [
        _DiggingLogSearchResponse.from_orm(digging_log) for digging_log in digging_logs
    ]
