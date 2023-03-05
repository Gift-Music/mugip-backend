import datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import expression as sql_exp
from sqlalchemy.dialects.postgresql import insert as pg_insert
from geoalchemy2 import WKTElement

from tests.mock.tag import create_tag

from app.ctx import AppCtx
from app.models import postgres as m
from app.utils import fastapi as fastapi_util
from app.constants import DEFAULT_SRID


async def create_digging_log() -> None:
    try:
        await create_tag()

        track_obj = await AppCtx.current.spotify_client.get_track(track_id='4fouWK6XVHhzl78KzQ1UjL')

        release_date = datetime.datetime.strptime(track_obj.album.release_date, '%Y-%M-%d')

        album = m.Album(
            id=track_obj.album.id,
            name=track_obj.album.name,
            release_date=release_date,
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
        AppCtx.current.db.session.add_all(images)

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
        AppCtx.current.db.session.add_all(artist_tracks)

        user: m.User = (
            await AppCtx.current.db.session.execute(
                sql_exp.select(m.User).where(m.User.id == 1)
            )
        ).scalar_one_or_none()

        tag: m.Tag = (
            await AppCtx.current.db.session.execute(
                sql_exp.select(m.Tag).where(m.Tag.name == 'test_tag')
            )
        ).scalar_one_or_none()

        coordinates = WKTElement(
            f"POINT(5 45)", srid=DEFAULT_SRID
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

    except IntegrityError as ex:
        print(ex)
        raise fastapi_util.LogicError(
            code="try_again",
            message="there is a race condition. try again.",
        )

    