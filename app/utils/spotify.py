from __future__ import annotations

import datetime
import logging
from base64 import b64encode
from functools import cached_property
from typing import Any

import httpx
import msgpack
from pydantic import BaseModel, dataclasses

from app.constants import TZ_UTC
from app.ctx import AppCtx
from app.models.services import Track

from .misc import lazystr

logger = logging.getLogger(__name__)

REDIS_KEYSPACE = lazystr(lambda: AppCtx.current.settings.REDIS_KEY_PREFIX + ":spotify")
SPOTIFY_AUTH_BASE_URL = "https://accounts.spotify.com"
SPOTIFY_API_BASE_URL = "https://api.spotify.com/v1"
SPOTIFY_AUTH_TOKEN = lazystr(
    lambda: b64encode(
        (
            AppCtx.settings.SPOTIFY_CLIENT_ID
            + ":"
            + AppCtx.settings.SPOTIFY_CLIENT_SECRET
        ).encode()
    ).decode()
)


@dataclasses.dataclass
class SpotifyUtilError(Exception):
    code: str
    message: str
    detail: dict[str, Any] | None = None


class SpotifyApiHandler:
    _default_token: str | None = None
    _default_token_expired_dt: datetime.datetime = datetime.datetime.fromtimestamp(
        0.0, tz=TZ_UTC
    )

    @cached_property
    async def client_credentials(self) -> str:
        if (
            self._default_token is None
            or self._default_token_expired_dt > datetime.datetime.now()
        ):
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    url=SPOTIFY_AUTH_BASE_URL + "/api/token",
                    data={
                        "grant_type": "client_credentials",
                    },
                    headers={"Authorization": f"Basic {SPOTIFY_AUTH_TOKEN}"},
                )

            resp_json = resp.json()

            self._default_token = resp_json["access_token"]
            self._default_token_expired_dt = (
                datetime.datetime.now() + datetime.timedelta(resp_json["expires_in"])
            )

        return self._default_token  # type: ignore

    async def _get_request(
        self,
        url: str,
        resp_model: type[BaseModel],
        params: dict[str, Any] | None = None,
        headers: dict[str, Any] | None = None,
    ) -> BaseModel:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                url,
                params=params,
                headers=headers,
            )

            if resp.status_code != 200:
                raise SpotifyUtilError(
                    code="failed_to_fetch_spotify_token",
                    message="something wrong",
                )

        return resp_model.parse_obj(resp.json())

    async def get_track(self, track_id: str) -> Track:
        track_key: str = f"{REDIS_KEYSPACE}:track:{track_id}"
        track_bytes: bytes | None = await AppCtx.current.redis.get(track_key)
        if track_bytes is not None:
            return Track.parse_obj(msgpack.loads(track_bytes))

        track: Track = await self._get_request(
            f"{SPOTIFY_API_BASE_URL}/tracks/{track_id}",
            resp_model=Track,
            headers={"Authorization": f"Bearer {await self.client_credentials}"},
        )  # type: ignore

        await AppCtx.current.redis.set(track_key, msgpack.dumps(track.dict()))

        return track
