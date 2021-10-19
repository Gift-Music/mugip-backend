from __future__ import annotations

import hashlib
import os
import sys
from functools import cached_property
from typing import Any, Optional, Union

import msgpack
from pydantic import BaseModel

__all__ = ['config']


ConfigValueType = Union[bool, int, float, str, bytes, None]


def load_config(config_path: str = 'configs/default.py') -> dict[str, ConfigValueType]:
    config_path_from_env = os.getenv('CONFIG_PATH')
    if config_path_from_env is not None:
        print('Replace config path with environment variable.',
              file=sys.stderr)
        config_path = config_path_from_env

    try:
        with open(config_path, encoding='utf-8') as f:
            config_source = f.read()
    except FileNotFoundError:
        print('Cannot find config file at "%s".' % config_path,
              file=sys.stderr)
        sys.exit(1)

    try:
        config_module_variables: dict[str, ConfigValueType] = dict()
        exec(config_source, config_module_variables)  # nosec
    except Exception:
        print('Failed to evaluate config file.', file=sys.stderr)
        sys.exit(1)

    config: dict[str, ConfigValueType] = dict()
    for k, v in config_module_variables.items():
        if not k.startswith('_') and k.isupper():
            config[k] = v

    return config


class ConfigTemplate(BaseModel):
    HOST_NAME: str
    LOGGING_DEBUG_LEVEL: bool

    DEBUG_ALLOW_CORS_ALL_ORIGIN: bool
    DEBUG_ALLOW_NON_CERTIFICATED_USER_GET_TOKEN: bool

    THREAD_POOL_SIZE: Optional[int]

    SECRET_KEY: str

    DATABASE_URI: str
    DATABASE_OPTIONS: dict[str, Any]

    REDIS_CONNECT_URI: str
    REDIS_CONNECT_CONFIG: dict[str, Any]
    REDIS_KEY_PREFIX: str

    ELASTICSEARCH_CONNECT_URI: str

    @cached_property
    def ident(self) -> str:
        return hashlib.sha256(msgpack.packb(self.dict())).hexdigest()

    class Config:
        allow_mutation = False
        keep_untouched = (cached_property,)


config = ConfigTemplate.parse_obj(load_config().items())
