import uuid

import asyncpg
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_scoped_session,
    create_async_engine,
)
from sqlalchemy.orm import sessionmaker

from app.ctx import AppCtx


async def _asyncpg_prepare(  # type: ignore
    self,
    query,
    *,
    name=None,
    timeout=None,
    record_class=None,
):
    return await self._prepare(
        query,
        name=str(uuid.uuid1()) if name is None else name,  # hotfix
        timeout=timeout,
        use_cache=False,
        record_class=record_class,
    )


class RdbConn:
    def __init__(self, db_uri: str) -> None:
        self.engine: AsyncEngine = create_async_engine(
            db_uri,
            connect_args={
                # to disable SQLA's statement cache for `.prepare()`
                "prepared_statement_cache_size": 0,
                # to disable asyncpg's statement cache for `.execute()`
                "statement_cache_size": 0,
            },
        )

        # hotfix for `https://github.com/sqlalchemy/sqlalchemy/issues/6467`
        asyncpg.Connection.prepare = _asyncpg_prepare

        self._scoped_session = async_scoped_session(
            sessionmaker(
                self.engine,
                class_=AsyncSession,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False,
            ),
            # NOTE : we cannot use `asyncio.current_task` because starlette schedules
            #        HTTPMiddleware and routing function in different tasks
            scopefunc=lambda: AppCtx.current.id,
        )

    @property
    def session(self) -> AsyncSession:
        return self._scoped_session()

    async def clear_scoped_session(self) -> None:
        await self._scoped_session.remove()
