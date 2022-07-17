import os
import sys
from logging.config import fileConfig

from alembic import context
from alembic.autogenerate import rewriter
from alembic.operations import ops
from sqlalchemy import engine_from_config, pool

config = context.config
fileConfig(config.config_file_name)  # type: ignore


sys.path.append(os.getcwd())


def _app_init():  # type: ignore
    from app.models.postgres import ModelBase
    from app.settings import AppSettings

    app_settings = AppSettings()

    config.set_main_option("sqlalchemy.url", app_settings.DATABASE_URI)
    return ModelBase.metadata


target_metadata = _app_init()


def _include_object(obj, name, type_, reflected, compare_to):  # type: ignore
    return True


writer = rewriter.Rewriter()


@writer.rewrites(ops.AddColumnOp)
def _(context, revision, op):  # type: ignore
    if op.column.nullable:
        return op
    else:
        op.column.nullable = True
        return [
            op,
            ops.AlterColumnOp(
                op.table_name,
                op.column.name,
                modify_nullable=False,
                existing_type=op.column.type,
            ),
        ]


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        include_object=_include_object,
        literal_binds=True,
        compare_server_default=True,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=_include_object,
            sqlalchemy_module_prefix="sa.",
            process_revision_directives=writer,
            compare_server_default=True,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
