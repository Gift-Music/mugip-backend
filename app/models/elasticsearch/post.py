from elasticsearch_dsl import GeoPoint, InnerDoc, Integer, Nested, Text

from .base_ import DEFAULT_TEXT_FIELDS, DocumnetBase


class Music(InnerDoc):
    artists = Text(fields=DEFAULT_TEXT_FIELDS)
    name = Text(fields=DEFAULT_TEXT_FIELDS)
    yt_song_id = Text()
    duration = Integer()


class Post(DocumnetBase):
    open_range = Integer(required=True)
    author_id = Integer(required=True)
    playlist = Nested(Music)
    coordinates = GeoPoint(required=True)
    tag = Text(fields=DEFAULT_TEXT_FIELDS)
