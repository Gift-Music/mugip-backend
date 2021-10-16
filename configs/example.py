

from typing import Any
from urllib.parse import urlencode


def _uri_builder(
    scheme: str, *,
    userid: str = '',
    userpw: str = '',
    host: str,
    port: int | None = None,
    path: str = '',
    options: dict[str, Any] | None = None,
) -> str:
    auth = f'{userid}:{userpw}@' if (userid or userpw) else ''
    port_str = f':{port}' if port is not None else ''
    options_str = urlencode(options or {})
    return f'{scheme}://{auth}{host}{port_str}/{path}?{options_str}'


LOGGING_DEBUG_LEVEL: bool = True

DEBUG_ALLOW_CORS_ALL_ORIGIN: bool = True
DEBUG_ALLOW_NON_CERTIFICATED_USER_GET_TOKEN: bool = True

THREAD_POOL_SIZE: int | None = None

SECRET_KEY: str = 'example_secret_key_example_secret_key_example_secret_key_example_secret_key'

DATABASE_URI: str = _uri_builder(
    'postgres',
    userid='mugip',
    userpw='devpassword',
    host='127.0.0.1',
    port=35000,
    path='mugip',  # DB name
    options={},
)
DATABASE_OPTIONS: dict[str, Any] = {
    'pool_pre_ping': True,
    'pool_recycle': 3 * 60,
    'pool_size': 100,
    'max_overflow': 0,
    'pool_use_lifo': True,
}

REDIS_CONNECT_URI: str = _uri_builder(
    'redis',
    host='127.0.0.1',
    port=25100,
    path='0',  # DB number
    options={},
)
REDIS_CONNECT_CONFIG: dict[str, Any] = {
    'retry_on_timeout': True,
    'max_connections': 20,
    'health_check_interval': 120,
}

ELASTICSEARCH_CONNECT_URI: str = _uri_builder(
    'http',
    host='127.0.0.1',
    port=35200,
    path='mugip',
    options={},
)

REDIS_KEY_PREFIX: str = 'dev:mugip:'  # Warning! Do not share with production server

