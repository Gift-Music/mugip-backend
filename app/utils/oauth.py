from __future__ import annotations

import dataclasses
import enum
import logging
from typing import Any

import httpx
from pydantic import BaseModel

from .spotify import SPOTIFY_AUTH_TOKEN, spotify_me_api

logger = logging.getLogger(__name__)


SOCIAL_API_TIMEOUT = 15.0
SPOTIFY_AUTH_BASE_URL = "https://accounts.spotify.com"
SPOTIFY_API_BASE_URL = "https://api.spotify.com/v1"


@dataclasses.dataclass
class OauthUtilError(Exception):
    code: str
    message: str
    detail: dict[str, Any] | None = None


class SocialInfo(BaseModel):
    uid: str
    email: str
    name: str


class ProviderTypeEnum(enum.IntEnum):
    Spotify = 0


async def get_social_token(
    code: str, redirect_uri: str, provider_type: ProviderTypeEnum
) -> tuple[str, str]:
    if provider_type == ProviderTypeEnum.Spotify:
        return await spotify_get_token(code, redirect_uri)
    else:
        raise OauthUtilError(
            code="invalid_provider_type",
            message="provider_type is not valid",
        )


async def get_social_info(token: str, provider_type: ProviderTypeEnum) -> SocialInfo:
    if provider_type == ProviderTypeEnum.Spotify:
        raw_info = await spotify_me_api(token)
    else:
        raise OauthUtilError(
            code="invalid_provider_type",
            message="provider_type is not valid",
        )

    return SocialInfo(
        uid=raw_info["id"],
        email=raw_info["email"],
        name=raw_info["display_name"],
    )


async def spotify_get_token(code: str, redirect_uri: str) -> tuple[str, str]:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            url=SPOTIFY_AUTH_BASE_URL + "/api/token",
            data={
                "code": code,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
            headers={"Authorization": f"Basic {SPOTIFY_AUTH_TOKEN}"},
        )

    if resp.status_code != 200:
        raise OauthUtilError(
            code="failed_to_fetch_spotify_token",
            message="something wrong",
            detail=resp.json(),
        )

    resp_json = resp.json()

    return resp_json["access_token"], resp_json["refresh_token"]
