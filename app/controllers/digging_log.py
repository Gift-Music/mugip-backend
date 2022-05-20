from __future__ import annotations
import datetime

from typing import Any, Dict, List, Literal, Optional

import jsonschema
from fastapi import Depends, Response
from pydantic import BaseModel, Field, validator
from sqlalchemy.orm import Session, contains_eager, joinedload
from sqlalchemy.sql import expression as sql_exp
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.models import postgres as m
from app.utils import AppUtils
from app.utils import fastapi as fastapi_util
from app.utils.auth import user_auth_required
from app.utils.fastapi import get_app_utils, get_db_session
from app.utils.filter_expr import build_filter_expr

router = fastapi_util.CustomAPIRouter(prefix='/digging_log', tags=['digging_log'])


class _DiggingLogPostRequest(BaseModel):
    track_id: str
    tag_name: str


@router.post('/')
async def digging_log_post_api(
    q: _DiggingLogPostRequest,
    db_session: Session = Depends(get_db_session),
    app_utils: AppUtils = Depends(get_app_utils),
    me_user_id: int = Depends(user_auth_required),
) -> None:
    track = db_session \
        .query(m.Track) \
        .filter(m.Track.id == q.track_id) \
        .one_or_none()

    if track is None:
        track_obj = await app_utils.spotify.get_track(q.track_id)
        album = db_session \
            .query(m.Album) \
            .filter(m.Album.id == track_obj.album.id) \
            .one_or_none()

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

        db_session.add(album)
        db_session.add_all(images)

        db_session.execute(
            pg_insert(m.Artist.__table__)
            .values([
                {
                    'id': artist.id,
                    'name': artist.name,
                }
                for artist in track_obj.artists
            ])
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
        db_session.add(track)
        db_session.add_all(artist_tracks)

    tag = db_session \
        .query(m.Tag) \
        .filter(m.Tag.name == q.tag_name) \
        .one_or_none()

    if tag is None:
        raise fastapi_util.LogicError(
            code='not_found_tag',
            message='failed to found tag by this name',
        )

    user = db_session \
        .query(m.User) \
        .filter(m.User.id == me_user_id) \
        .one_or_none()

    if user is None:
        raise fastapi_util.LogicError(
            code='not_found_user',
            message='failed to found user by this id',
        )

    digging_log = m.DiggingLog(
        user=user,
        track=track,
    )

    db_session.add(digging_log)

    db_session.add(
        m.DiggingLogTag(
            digging_log=digging_log,
            tag=tag,
        )
    )

    db_session.commit()


_DiggingLogSearchRequestFilterExpr = build_filter_expr({
    'user_id': {'type': 'integer'},
    'track_id': {'type': 'string'},
    'tag_name': {'type': 'string'},
})


class _DiggingLogSearchRequest(BaseModel):
    filter_expr: Optional[Dict[str, Any]] = Field(description=_DiggingLogSearchRequestFilterExpr.description)
    sort_by_key: Optional[Literal['created', 'updated']]
    sort_by_order: Optional[Literal['asc', 'desc']]
    offset: int = Field(ge=0)
    count: int = Field(ge=1, le=100)

    @validator('filter_expr')
    def validator_filter_expr(cls, value: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
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


@router.post('/search')
def digging_log_search_api(
    q: _DiggingLogSearchRequest,
    response: Response,
    db_session: Session = Depends(get_db_session),
    me_user_id: int = Depends(user_auth_required),
) -> List[_DiggingLogSearchResponse]:
    digging_logs_query = db_session \
        .query(m.DiggingLog) \
        .join(m.DiggingLog.digging_log_tags) \
        .options(
            contains_eager(m.DiggingLog.digging_log_tags),
            joinedload(m.DiggingLog.track),
        )

    if q.filter_expr is not None:
        digging_logs_query = digging_logs_query \
            .filter(
                _DiggingLogSearchRequestFilterExpr.to_query(
                    q.filter_expr,
                    {
                        'user_id': m.DiggingLog.user_id.__eq__,
                        'track_id': m.DiggingLog.track_id.__eq__,
                        'tag_name': m.Tag.name.ilike,
                    }
                )
            )

    sort_by_col = {
        'created': m.Tag.created,
        'updated': m.Tag.updated,
    }[q.sort_by_key or 'id']

    sort_by_order_exp = {
        'asc': sql_exp.asc,
        'desc': sql_exp.desc,
    }[q.sort_by_order or 'asc']

    digging_logs_count = digging_logs_query.count()
    response.headers['x-total'] = str(digging_logs_count)

    digging_logs = digging_logs_query \
        .order_by(sort_by_order_exp(sort_by_col)) \
        .slice(q.offset, q.offset + q.count) \
        .all()

    return [
        _DiggingLogSearchResponse.from_orm(digging_log)
        for digging_log in digging_logs
    ]
