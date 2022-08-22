from __future__ import annotations

import dataclasses
import enum
import logging
from typing import Any

import httpx
import jwt
import jwt.utils
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicNumbers
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from pydantic import BaseModel

from app.ctx import AppCtx

from .spotify import SPOTIFY_AUTH_TOKEN

logger = logging.getLogger(__name__)


SOCIAL_API_TIMEOUT = 15.0
SPOTIFY_AUTH_BASE_URL = "https://accounts.spotify.com"
SPOTIFY_API_BASE_URL = "https://api.spotify.com/v1"

KAKAO_API_BASE_URL = "https://kapi.kakao.com/v2"

APPLE_API_AUTH_KEY_URL = "https://appleid.apple.com/auth/keys"
APPLE_OAUTH_PUBLIC_KEY_LIFETIME = 30 * 24 * 60 * 60  # 30 days

GOOGLE_API_BASE_URL = "https://www.googleapis.com"
GOOGLE_API_VERSION = "v2"


def _convert_to_dec(s: str) -> int:
    return int(jwt.utils.base64url_decode(s).hex(), 16)


async def _get_apple_public_key(kid: str) -> bytes:
    async with httpx.AsyncClient() as client:
        apple_response_raw = await client.get(
            APPLE_API_AUTH_KEY_URL, timeout=SOCIAL_API_TIMEOUT
        )

    apple_response = apple_response_raw.json()

    for key in apple_response["keys"]:
        if key["kid"] == kid:
            modulus = key["n"]
            exponent = key["e"]
            break
    else:
        raise Exception(f"There is no matching key in the apple response: {kid}")

    return (
        RSAPublicNumbers(_convert_to_dec(exponent), _convert_to_dec(modulus))
        .public_key(default_backend())
        .public_bytes(Encoding.PEM, PublicFormat.PKCS1)
    )


@dataclasses.dataclass
class OauthUtilError(Exception):
    code: str
    message: str
    detail: dict[str, Any] | None = None


class SocialInfo(BaseModel):
    uid: str
    email: str | None = None
    name: str | None = None
    profile_url: str | None = None
    gender: str | None = None
    birthday: str | None = None
    phone: str | None = None


class ProviderTypeEnum(enum.Enum):
    Spotify = "Spotify"
    Kakao = "Kakao"
    Apple = "Apple"
    Google = "Google"


async def kakao_me_api(token: str) -> SocialInfo:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{KAKAO_API_BASE_URL}/user/me",
            params={"secure_resource": True},
            headers={"Authorization": f"Bearer {token}"},
        )

    if resp.status_code != 200:
        raise OauthUtilError(
            code="invalid_response",
            message="kakao response is invalid",
        )
    try:
        kakao_me = resp.json()
        uid = str(kakao_me["id"])
        kakao_account = kakao_me.get("kakao_account", {})
        profile_url: str = kakao_account.get("profile", {}).get("thumbnail_image_url")
        email: str | None = kakao_account.get("email")
        name: str | None = kakao_account.get("name")
        gender: str | None = kakao_account.get("gender")
        birthday: str | None = kakao_account.get("birthday")
        phone: str | None = kakao_account.get("phone_number")

    except Exception:
        logger.exception("Kakao returned unexpected result")
        raise OauthUtilError(
            code="unexpected_result",
            message="Kakao returned unexpected result",
        )

    return SocialInfo(
        uid=uid,
        email=email,
        name=name,
        profile_url=profile_url,
        gender=gender,
        birthday=birthday,
        phone=phone,
    )


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


async def spotify_me_api(token: str) -> SocialInfo:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            url=SPOTIFY_API_BASE_URL + "/me",
            headers={"Authorization": f"Bearer {token}"},
        )

    if resp.status_code != 200:
        raise OauthUtilError(
            code="failed_to_fetch_spotify_profile",
            message="something wrong",
        )

    spotify_me = resp.json()

    return SocialInfo(
        uid=spotify_me["id"],
        profile_url=spotify_me["images"][0]["url"],
        name=spotify_me["display_name"],
    )


async def parse_apple_id_token(apple_id_token: str) -> SocialInfo:
    try:
        headers = jwt.get_unverified_header(apple_id_token)

        kid = headers["kid"]

        message = jwt.decode(apple_id_token, options={"verify_signature": False})

        audience = message["aud"]

        if audience not in AppCtx.current.settings.APPLE_OAUTH_CLIENT_ID_LIST:
            raise Exception("invalid audience")

        public_key = await _get_apple_public_key(kid)

        decoded = jwt.decode(
            apple_id_token,
            public_key,  # type: ignore
            algorithms=["RS256"],
            audience=audience,
        )

    except Exception as ex:
        raise OauthUtilError(
            code="invalid_token",
            message=f"The apple id_token is not valid: {str(ex)}",
        )

    return SocialInfo(
        uid=decoded["sub"],
        email=decoded["email"],
    )


async def google_me_api(token: str) -> SocialInfo:
    async with httpx.AsyncClient() as client:
        try:
            google_response = await client.get(
                f"{GOOGLE_API_BASE_URL}/oauth2/v2/userinfo",
                headers={"Authorization": "Bearer " + token},
                timeout=SOCIAL_API_TIMEOUT,
            )
        except Exception:
            logger.exception("Cannot connect to Google API")
            raise OauthUtilError(
                code="cannot_connect",
                message="Cannot connect to Google API",
            )

    if google_response.status_code not in range(200, 300):
        raise OauthUtilError(
            code="invalid_token",
            message="Google API rejected the token",
        )

    try:
        google_me = google_response.json()
        google_uid = str(google_me["id"])
        profile_url = google_me["picture"]
    except Exception:
        logger.exception("Google API returned unexpected result")
        raise OauthUtilError(
            code="unexpected_result",
            message="Google API returned unexpected result",
        )

    return SocialInfo(
        uid=google_uid,
        profile_url=profile_url,
    )


async def get_social_info(token: str, provider_type: ProviderTypeEnum) -> SocialInfo:
    match provider_type:
        case ProviderTypeEnum.Spotify:
            return await spotify_me_api(token)
        case ProviderTypeEnum.Kakao:
            return await kakao_me_api(token)
        case ProviderTypeEnum.Apple:
            return await parse_apple_id_token(token)
        case ProviderTypeEnum.Google:
            return await google_me_api(token)
        case _:
            raise OauthUtilError(
                code="invalid_provider_type",
                message="provider_type is not valid",
            )
