from __future__ import annotations

import dataclasses
import enum
import logging

import httpx

logger = logging.getLogger(__name__)


KAKAO_API_BASE_URL = 'https://kapi.kakao.com'
KAKAO_API_VERSION = 'v2'

GOOGLE_API_BASE_URL = 'https://www.googleapis.com'
GOOGLE_API_VERSION = 'v2'

SOCIAL_API_TIMEOUT = 15.0


@dataclasses.dataclass
class OauthUtilError(Exception):
    code: str
    message: str


class ProviderTypeEnum(enum.IntEnum):
    Google = 1
    Kakao = 2


def get_social_uid_by_token_n_provider_type(token: str, provider_type: ProviderTypeEnum) -> str:
    if provider_type == ProviderTypeEnum.Google:
        return google_me_api(token)
    elif provider_type == ProviderTypeEnum.Kakao:
        return kakao_me_api(token)
    else:
        raise OauthUtilError(
            code='invalid_provider_type',
            message='provider_type is not valid',
        )


def _google_uri_builder(endpoint: str) -> str:
    uri = '{}/{}/{}{}'.format(
        GOOGLE_API_BASE_URL,
        'oauth2',
        GOOGLE_API_VERSION,
        endpoint
    )
    return uri


def google_me_api(google_token: str) -> str:
    google_me_uri = _google_uri_builder('/userinfo')

    try:
        google_response = httpx.get(
            google_me_uri,
            headers={'Authorization': 'Bearer ' + google_token},
            timeout=SOCIAL_API_TIMEOUT,
        )
    except Exception:
        raise OauthUtilError(
            code='cannot_connect',
            message='Cannot connect to Google API',
        )

    if google_response.status_code not in range(200, 300):
        raise OauthUtilError(
            code='invalid_token',
            message='Google API rejected the token',
        )

    try:
        google_me = google_response.json()

        google_uid = str(google_me['id'])
    except Exception:
        raise OauthUtilError(
            code='unexpected_result',
            message='Google API returned unexpected result',
        )

    return google_uid


def _kakao_uri_builder(endpoint: str) -> str:
    uri = '{}/{}/{}'.format(
        KAKAO_API_BASE_URL, KAKAO_API_VERSION, endpoint
    )
    return uri


def kakao_me_api(kakao_token: str) -> str:
    kakao_me_uri = _kakao_uri_builder('/user/me')

    try:
        kakao_response = httpx.get(
            kakao_me_uri,
            headers={'Authorization': 'Bearer ' + kakao_token, 'propertyKeys': '[]'},
            timeout=SOCIAL_API_TIMEOUT,
        )
    except Exception:
        raise OauthUtilError(
            code='cannot_connect',
            message='Cannot connect to Kakao',
        )

    if kakao_response.status_code not in range(200, 300):
        raise OauthUtilError(
            code='invalid_token',
            message='Kakao rejected the token',
        )

    try:
        kakao_me = kakao_response.json()

        kakao_uid = str(kakao_me['id'])
    except Exception:
        raise OauthUtilError(
            code='unexpected_result',
            message='Kakao returned unexpected result',
        )

    return kakao_uid
