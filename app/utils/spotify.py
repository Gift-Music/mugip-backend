from __future__ import annotations

import datetime
import logging
from base64 import b64encode
from functools import cached_property
from typing import Any, Optional

import httpx
from pydantic import BaseModel, dataclasses

from app.models import services as m
from app.utils.base_ import AppUtilBase

logger = logging.getLogger(__name__)


SPOTIFY_AUTH_BASE_URL = 'https://accounts.spotify.com'
SPOTIFY_API_BASE_URL = 'https://api.spotify.com/v1'


@dataclasses.dataclass
class SpotifyUtilError(Exception):
    code: str
    message: str
    detail: Optional[dict[str, Any]]


class SpotifyAppUtil(AppUtilBase):
    _default_token: str | None = None
    _default_token_expired_dt: datetime.datetime | None = None

    @cached_property
    def redis_keyspace(self) -> str:
        return f'{self.app_settings.REDIS_KEY_PREFIX}:spotify'

    @cached_property
    def auth_token(self) -> str:
        return b64encode(
            (self.app_settings.SPOTIFY_CLIENT_ID + ':' + self.app_settings.SPOTIFY_CLIENT_SECRET).encode()
        ).decode()

    @property
    async def default_access_token(self) -> str:
        if (
            self._default_token is None
            or self._default_token_expired_dt > datetime.datetime.now()
        ):
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    url=SPOTIFY_AUTH_BASE_URL + '/api/token',
                    data={
                        'grant_type': 'client_credentials',
                    },
                    headers={'Authorization': f'Basic {self.auth_token}'}
                )
                print(resp.json())

            resp_json = resp.json()

            self._default_token = resp_json['access_token']
            self._default_token_expired_dt = datetime.datetime.now() + datetime.timedelta(resp_json['expires_in'])

        return self._default_token

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
                    code='failed_to_fetch_spotify_token',
                    message='something wrong',
                )

        return resp_model.parse_obj(resp.json())

    async def get_track(self, track_id: str) -> m.Track:
        track = self.app_context.redis.get(f'{self.redis_keyspace}:track:{track_id}')
        return (
            track
            if track is not None
            else await self._get_request(
                f'{SPOTIFY_API_BASE_URL}/tracks/{track_id}',
                resp_model=m.Track,
                headers={'Authorization': f'Bearer {await self.default_access_token}'},
            )
        )


async def spotify_me_api(token: str) -> dict[str, Any]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            url=SPOTIFY_API_BASE_URL + '/me',
            headers={'Authorization': f'Bearer {token}'},
        )

        if resp.status_code != 200:
            raise SpotifyUtilError(
                code='failed_to_fetch_spotify_profile',
                message='something wrong',
            )

    return resp.json()
