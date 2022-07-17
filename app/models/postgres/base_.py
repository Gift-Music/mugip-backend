from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import text as sql_text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import object_session
from sqlalchemy.schema import Column, FetchedValue, Sequence
from sqlalchemy.sql import sqltypes

if TYPE_CHECKING:
    from sqlalchemy.ext.declarative import DeclarativeMeta
    from sqlalchemy.orm.session import Session
    from sqlalchemy.sql.schema import ColumnCollectionConstraint, MetaData, Table

ModelMeta: DeclarativeMeta = declarative_base()


def _table_guid_generator(constraint: ColumnCollectionConstraint, table: Table) -> str:
    str_tokens = [table.name] + [col.name for col in constraint.columns]
    guid = uuid.uuid5(uuid.NAMESPACE_OID, "_".join(str_tokens))
    return guid.hex


ModelMeta.metadata.naming_convention = {
    "guid": _table_guid_generator,
    "pk": "pk_%(table_name)s",
    "ix": "ix_%(guid)s",
    "uq": "uq_%(guid)s",
    "fk": "fk_%(guid)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
}


class ModelBase(ModelMeta):
    __abstract__ = True

    __table__: Table
    metadata: MetaData

    created = Column(
        sqltypes.TIMESTAMP(timezone=True),
        nullable=False,
        server_default=sql_text("CURRENT_TIMESTAMP"),
    )
    updated = Column(
        sqltypes.TIMESTAMP(timezone=True),
        nullable=False,
        server_default=sql_text("CURRENT_TIMESTAMP"),
        server_onupdate=FetchedValue(),
    )

    @property
    def object_session(self) -> Session:
        return object_session(self)  # type: ignore


OrderHintSequence: Sequence[int] = Sequence(
    "order_hint_seq", metadata=ModelBase.metadata
)
