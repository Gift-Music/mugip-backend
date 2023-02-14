from typing import List, Optional

import httpx
from fastapi import Depends
from pydantic import BaseModel

from app.models.services.music import Artist, Track
from app.utils import fastapi as fastapi_util
from app.utils import spotify as spotify_util
from app.utils.auth import user_auth_required

router = fastapi_util.CustomAPIRouter(prefix="/music", tags=["music"])


SPOTIFY_URL = "https://api.spotify.com/v1"
DEFAULT_HEADER = {
    "Accept": "application/json",
    "Content-Type": "application/json",
}


class _MusicSearchResponse(BaseModel):
    tracks: List[Track]


@router.get("/track")
async def music_track_search_api(
    q: str,
    offset: int = 0,
    limit: int = 10,
    spotify_access_token: Optional[str] = Depends(
        fastapi_util.get_spotify_access_token
    ),
    me_user_id: int = Depends(user_auth_required),
) -> _MusicSearchResponse:
    async with httpx.AsyncClient() as client:
        spfy_handler = spotify_util.SpotifyApiHandler()
        response = await client.get(
            f"{SPOTIFY_URL}/search",
            params={
                "q": q,
                "type": "track",
                "market": "KR",
                "offset": offset,
                "limit": limit,
            },
            headers={
                **DEFAULT_HEADER,
                "Authorization": f"Bearer {await spfy_handler.client_credentials}",
            },
        )

        if response.status_code != 200:
            raise fastapi_util.LogicError(
                code="spotify_error",
                message="spotify_error",
            )

    return _MusicSearchResponse(
        tracks=[Track.parse_obj(track) for track in response.json()["tracks"]["items"]]
    )


class _MusicTrackGetResponse(BaseModel):
    track: Track


@router.get("/track/{track_id:str}")
async def music_track_get_api(
    track_id: str,
    spotify_access_token: Optional[str] = Depends(
        fastapi_util.get_spotify_access_token
    ),
    me_user_id: int = Depends(user_auth_required),
) -> _MusicTrackGetResponse:
    if spotify_access_token is None:
        raise fastapi_util.LogicError(
            code="no_access_token",
            message="you should send spotify access token",
        )

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{SPOTIFY_URL}/tracks/{track_id}",
            headers={
                **DEFAULT_HEADER,
                "Authorization": f"Bearer {spotify_access_token}",
            },
        )

        if response.status_code != 200:
            raise fastapi_util.LogicError(
                code="spotify_error",
                message="spotify_error",
            )

    return _MusicTrackGetResponse(track=Track.parse_obj(response.json()))


class _MusicArtistGetResponse(BaseModel):
    artist: Artist


@router.get("/artist/{artist_id:str}")
async def music_artist_get_api(
    artist_id: str,
    spotify_access_token: Optional[str] = Depends(
        fastapi_util.get_spotify_access_token
    ),
    me_user_id: int = Depends(user_auth_required),
) -> _MusicArtistGetResponse:
    if spotify_access_token is None:
        raise fastapi_util.LogicError(
            code="no_access_token",
            message="you should send spotify access token",
        )

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{SPOTIFY_URL}/artists/{artist_id}",
            headers={
                **DEFAULT_HEADER,
                "Authorization": f"Bearer {spotify_access_token}",
            },
        )

        if response.status_code != 200:
            raise fastapi_util.LogicError(
                code="spotify_error",
                message="spotify_error",
            )

    return _MusicArtistGetResponse(artist=Artist.parse_obj(response.json()))
