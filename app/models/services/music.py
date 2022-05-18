from typing import List, Optional

from pydantic import BaseModel


class Image(BaseModel):
    height: int
    url: str
    width: int


class ExternalUrls(BaseModel):
    spotify: str


class Artist(BaseModel):
    id: str
    name: str
    external_urls: ExternalUrls
    uri: str


class Album(BaseModel):
    id: str
    name: str
    release_date: str
    album_type: str
    total_tracks: int
    uri: str
    images: List[Image]
    external_urls: ExternalUrls


class Track(BaseModel):
    id: str
    album: Album
    artists: List[Artist]
    duration_ms: int
    external_urls: ExternalUrls
    track_number: int
    preview_url: Optional[str]
