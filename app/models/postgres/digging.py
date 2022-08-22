from geoalchemy2 import Geography
from sqlalchemy import DDL, event
from sqlalchemy import func as sql_func
from sqlalchemy import orm as sql_orm
from sqlalchemy import sql as sql_exp
from sqlalchemy.orm import relationship
from sqlalchemy.schema import Column
from sqlalchemy.sql import sqltypes
from sqlalchemy.sql.schema import ForeignKey

from app.constants import DEFAULT_SRID

from .base_ import ModelBase
from .user import User


class Artist(ModelBase):
    __tablename__ = "artist"

    id = Column(sqltypes.String, nullable=False, primary_key=True)
    name = Column(sqltypes.String, nullable=False)

    tracks: list["ArtistTrack"] = relationship(
        "ArtistTrack", back_populates="artist", uselist=True, cascade="all"
    )


class Album(ModelBase):
    __tablename__ = "album"

    id = Column(sqltypes.String, nullable=False, primary_key=True)

    name = Column(sqltypes.String, nullable=False, index=True)
    release_date = Column(sqltypes.TIMESTAMP(timezone=True), nullable=False)
    total_tracks = Column(sqltypes.Integer, nullable=False)

    images: list["Image"] = relationship(
        "Image", uselist=True, back_populates="album", cascade="all"
    )
    tracks: list["Track"] = relationship(
        "Track", uselist=True, back_populates="album", cascade="all"
    )


class Track(ModelBase):
    __tablename__ = "track"

    id = Column(sqltypes.String, nullable=False, primary_key=True)

    album_id = Column(sqltypes.String, ForeignKey(Album.id))
    album: "Album" = relationship("Album", uselist=False)

    artist_tracks: list["ArtistTrack"] = relationship(
        "ArtistTrack", back_populates="track", uselist=True
    )
    artists = sql_orm.ColumnProperty

    digging_logs: list["DiggingLog"] = relationship(
        "DiggingLog", back_populates="track", uselist=True
    )

    duration_ms = Column(sqltypes.Float, nullable=False)
    track_number = Column(sqltypes.Integer, nullable=False)
    preview_url = Column(sqltypes.String, nullable=False)


class ArtistTrack(ModelBase):
    __tablename__ = "artist_track"

    artist_id = Column(
        sqltypes.String, ForeignKey(Artist.id), nullable=False, primary_key=True
    )
    artist = relationship("Artist", uselist=False)

    track_id = Column(
        sqltypes.String,
        ForeignKey(Track.id),
        nullable=False,
        primary_key=True,
        index=True,
    )
    track = relationship("Track", uselist=False)


class Tag(ModelBase):
    __tablename__ = "digging_tag"

    name = Column(sqltypes.String, nullable=False, primary_key=True)
    icon = Column(sqltypes.String, nullable=False)


class DiggingLog(ModelBase):
    __tablename__ = "digging_log"

    id = Column(sqltypes.Integer, nullable=False, primary_key=True)

    user_id = Column(sqltypes.Integer, ForeignKey(User.id), nullable=False)
    user = relationship("User", uselist=False)

    track_id = Column(sqltypes.String, ForeignKey(Track.id), nullable=False)
    track = relationship("Track", uselist=False, cascade="all")

    coordinates = Column(
        Geography(geometry_type="POINT", srid=DEFAULT_SRID, spatial_index=True),
        nullable=True,
    )

    digging_log_tags = relationship(
        "DiggingLogTag", back_populates="digging_log", uselist=True, cascade="all"
    )
    tags = sql_orm.ColumnProperty


class DiggingLogTag(ModelBase):
    __tablename__ = "digging_log_tag"

    digging_log_id = Column(
        sqltypes.Integer, ForeignKey(DiggingLog.id), nullable=False, primary_key=True
    )
    digging_log = relationship("DiggingLog", uselist=False)

    tag_name = Column(
        sqltypes.String, ForeignKey(Tag.name), nullable=False, primary_key=True
    )
    tag = relationship("Tag", uselist=False)


class Image(ModelBase):
    __tablename__ = "image"

    id = Column(sqltypes.Integer, nullable=False, primary_key=True)

    album_id = Column(sqltypes.String, ForeignKey(Album.id), nullable=False)
    album = relationship("Album", uselist=False)

    width = Column(sqltypes.Integer, nullable=False)
    height = Column(sqltypes.Integer, nullable=False)
    url = Column(sqltypes.String, nullable=False)


Track.artists = sql_orm.column_property(
    (
        sql_exp.select(
            [
                sql_func.coalesce(
                    sql_func.array_agg(
                        sql_func.json_build_object("id", Artist.id, "name", Artist.name)
                    ),
                    [],
                )
            ]
        )
        .select_from(
            sql_exp.join(
                ArtistTrack,  # type: ignore
                Artist,
            ),
        )
        .where(ArtistTrack.track_id == Track.id)
        .label("artists")
    ),
    deferred=False,
)


DiggingLog.tags = sql_orm.column_property(
    (
        sql_exp.select(
            [
                sql_func.coalesce(
                    sql_func.array_agg(
                        sql_func.json_build_object("name", Tag.name, "icon", Tag.icon)
                    ),
                    [],
                )
            ]
        )
        .select_from(
            sql_exp.join(
                Tag,  # type: ignore
                DiggingLogTag,
            ),
        )
        .where(DiggingLog.id == DiggingLogTag.digging_log_id)
        .label("tags")
    ),
    deferred=False,
)

event.listen(
    DiggingLog.__table__,
    "before_create",
    DDL("CREATE EXTENSION IF NOT EXISTS postgis;"),
)
