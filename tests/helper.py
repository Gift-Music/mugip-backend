import contextlib
from typing import AsyncIterator, Callable
from typing import Any

from app.ctx import AppCtx, bind_app_ctx, create_app_ctx
from app.models.postgres.base_ import ModelBase
from app.settings import AppSettings


@contextlib.asynccontextmanager
async def with_app_ctx(app_settings: AppSettings) -> AsyncIterator[AppCtx]:
    app_ctx = await create_app_ctx(app_settings)
    async with bind_app_ctx(app_ctx):
        yield app_ctx


async def ensure_fresh_env() -> None:
    async with AppCtx.current.db.engine.begin() as conn:
        await conn.run_sync(ModelBase.metadata.drop_all)
        await conn.run_sync(ModelBase.metadata.create_all)
    await AppCtx.current.redis.flushall()


class FakeResponse:
    def __init__(self, data: dict[str, Any], status_code: int):
        self.data = data
        self.status_code = status_code

    def json(self) -> dict[str, Any]:
        return self.data


def create_async_function(func: Callable) -> Callable:
    async def _func(*args, **kwargs) -> Any:  # type: ignore
        return func(*args, **kwargs)

    return _func
