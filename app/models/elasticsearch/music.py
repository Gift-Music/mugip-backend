from elasticsearch_dsl import Integer, Text

from .base_ import DEFAULT_TEXT_FIELDS, DocumnetBase


class Music(DocumnetBase):
    artists = Text(fields=DEFAULT_TEXT_FIELDS)
    name = Text(fields=DEFAULT_TEXT_FIELDS)
    yt_song_id = Text()
    duration = Integer()
