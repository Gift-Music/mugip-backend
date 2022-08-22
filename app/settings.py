from __future__ import annotations

import socket
from typing import Any, Dict, Optional

from pydantic import AnyUrl, BaseSettings, Field


class AppSettings(BaseSettings):
    LOGGING_DEBUG_LEVEL: bool = Field(
        default=True,
        description="True: DEBUG mode, False:: INFO mode",
    )

    DEBUG_ALLOW_CORS_ALL_ORIGIN: bool = Field(
        default=True,
        description="If True, allow origins for CORS requests.",
    )
    DEBUG_ALLOW_NON_CERTIFICATED_USER_GET_TOKEN: bool = Field(
        default=True,
        description="If True, allow non-cerficiated users to get ESP token.",
    )

    THREAD_POOL_SIZE: Optional[int] = Field(
        default=10,
        description="Change the server's thread pool size to handle non-async function",
    )

    SECRET_KEY: str = Field(
        default="example_secret_key_WoW",
        description="Secret key to be used for issuing HMAC tokens.",
    )

    DATABASE_URI: AnyUrl = Field(
        default="postgresql+asyncpg://mugip:devpassword@127.0.0.1:35000/mugip",
        description="PosstgreSQL connection URI.",
    )
    DATABASE_OPTIONS: Dict[str, Any] = Field(
        default={
            "connect_args": {
                "keepalives": 1,
                "keepalives_idle": 30,
                "keepalives_interval": 15,
            },
            "pool_pre_ping": True,
            "pool_recycle": 15 * 60,
            "pool_size": 50,
            "max_overflow": 50,
            "pool_use_lifo": True,
        },
        description="PosstgreSQL option to create a connection.",
    )

    REDIS_CONNECT_URI: AnyUrl = Field(
        default="redis://127.0.0.1:35100/0",
        description="Redis connection URI.",
    )
    REDIS_CONNECT_CONFIG: Dict[str, Any] = Field(
        default={
            # pool options
            "max_connections": 20,
            # connection options
            "socket_keepalive": True,
            "socket_keepalive_options": {
                # socket.TCP_KEEPIDLE: 30,
                socket.TCP_KEEPINTVL: 15,
            },
            "retry_on_timeout": True,
            "health_check_interval": 120,
        },
        description="Redis option to create a connection.",
    )
    REDIS_KEY_PREFIX: str = Field(
        default="dev:mugip:",
        description="Redis key prefix.",
    )

    SENDER_MAIL: str = Field(
        default="mugip.giftmusic@gmail.com",
        description="sender account for verify email",
    )

    SENDER_MAIL_PASSWORD: str = Field(
        default="", description="sender account's app password"
    )

    SPOTIFY_CLIENT_ID: str = Field(
        default="",
        description="spotify client id",
    )
    SPOTIFY_CLIENT_SECRET: str = Field(
        default="",
        description="spotify client secret",
    )

    APPLE_OAUTH_CLIENT_ID_LIST: list[str] = Field(
        default=[],
        description="Apple client id list",
    )

    AWS_ACCESS_KEY_ID: str = Field(default="", description="aws access key id")
    AWS_SECRET_ACCESS_KEY: str = Field(default="", description="aws secret access key")

    class Config:
        env_file = ".env"
        env_prefix = "mugip_"
