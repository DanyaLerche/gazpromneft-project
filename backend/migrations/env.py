from __future__ import annotations

import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from backend.database import Base
from config import settings

# Добавляем корень проекта в sys.path, если запускаем alembic из корня
if "" not in sys.path:
    sys.path.insert(0, "")

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Метаданные SQLAlchemy для автогенерации
target_metadata = Base.metadata


def get_url() -> str:
    url = settings.DATABASE_URL
    return url.replace("+asyncpg", "+psycopg2")


def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(
        get_url(),
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=True,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

