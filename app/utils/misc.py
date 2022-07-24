from __future__ import annotations

import datetime
from typing import Any, Callable

from app.constants import TZ_UTC


class lazystr:
    def __init__(self, func: Callable[[], str]) -> None:
        self._func = func

    def __str__(self) -> str:
        return self._func()

    def __add__(self, other: str) -> str:
        return self._func() + other

    def __mod__(self, other: str) -> str:
        return self._func() % other


def ts_to_dt(ts: int) -> datetime.datetime:
    return datetime.datetime.fromtimestamp(ts / 1000, tz=TZ_UTC)


def dt_to_ts(dt: datetime.datetime) -> int:
    return int(dt.timestamp() * 1000)


def msgpack_decoder(obj: Any) -> Any:
    if "__datetime__" in obj:
        obj = datetime.datetime.fromtimestamp(obj["ts"], tz=TZ_UTC)
    return obj


def msgpack_encoder(obj: Any) -> Any:
    if isinstance(obj, datetime.datetime):
        return {
            "__datetime__": True,
            "ts": obj.timestamp(),
        }
    return obj


def to_dot_format(dt_str: str) -> str:
    return f"{dt_str[0:4]}. {dt_str[4:6]}. {dt_str[6:8]}"
