from __future__ import annotations

import importlib
import uuid
from types import SimpleNamespace
from typing import Iterator

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, make_url

from config import settings

MIGRATION_MODULE = "backend.migrations.versions.000000000005_rbac_roles_and_project_metadata"


def _sync_database_url() -> str:
    return settings.DATABASE_URL.replace("+asyncpg", "+psycopg2")


def _execute_batch(engine: Engine, sql: str) -> None:
    raw_connection = engine.raw_connection()
    try:
        cursor = raw_connection.cursor()
        cursor.execute(sql)
        raw_connection.commit()
        cursor.close()
    finally:
        raw_connection.close()


def _prepare_legacy_schema(engine: Engine) -> None:
    _execute_batch(
        engine,
        """
CREATE SCHEMA tracker;

CREATE TYPE tracker.project_role AS ENUM ('project_member', 'project_admin', 'project_owner');

CREATE OR REPLACE FUNCTION tracker.set_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at := now();
  RETURN NEW;
END;
$$;

CREATE TABLE tracker.users (
  id uuid PRIMARY KEY,
  email text NOT NULL UNIQUE,
  full_name text NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE tracker.projects (
  id uuid PRIMARY KEY,
  key text NOT NULL UNIQUE,
  name text NOT NULL,
  created_by uuid NOT NULL REFERENCES tracker.users(id) ON DELETE RESTRICT,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE tracker.project_users (
  project_id uuid NOT NULL REFERENCES tracker.projects(id) ON DELETE CASCADE,
  user_id uuid NOT NULL REFERENCES tracker.users(id) ON DELETE CASCADE,
  role tracker.project_role NOT NULL DEFAULT 'project_member',
  joined_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (project_id, user_id)
);
        """,
    )


def _run_upgrade(engine: Engine, monkeypatch: pytest.MonkeyPatch) -> None:
    module = importlib.import_module(MIGRATION_MODULE)
    monkeypatch.setattr(module, "op", SimpleNamespace(execute=lambda sql: _execute_batch(engine, sql)))
    module.upgrade()


@pytest.fixture()
def migration_engine() -> Iterator[Engine]:
    sync_url = make_url(_sync_database_url())
    database_name = f"codex_rbac_migration_{uuid.uuid4().hex}"
    admin_engine = create_engine(sync_url, isolation_level="AUTOCOMMIT")

    try:
        with admin_engine.connect() as connection:
            connection.exec_driver_sql(f"CREATE DATABASE {database_name}")
    except Exception as exc:
        admin_engine.dispose()
        pytest.skip(f"PostgreSQL temp database is unavailable for migration tests: {exc}")

    engine = create_engine(sync_url.set(database=database_name))
    try:
        yield engine
    finally:
        engine.dispose()
        with admin_engine.connect() as connection:
            connection.execute(
                text(
                    """
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = :database_name
  AND pid <> pg_backend_pid()
                    """
                ),
                {"database_name": database_name},
            )
            connection.exec_driver_sql(f"DROP DATABASE IF EXISTS {database_name}")
        admin_engine.dispose()


def test_upgrade_backfills_and_defaults_app_role(migration_engine: Engine, monkeypatch: pytest.MonkeyPatch):
    _prepare_legacy_schema(migration_engine)

    demo_user_id = str(uuid.uuid4())
    legacy_user_id = str(uuid.uuid4())
    future_user_id = str(uuid.uuid4())

    with migration_engine.begin() as connection:
        connection.execute(
            text(
                """
INSERT INTO tracker.users (id, email, full_name, is_active)
VALUES
  (:demo_user_id, 'demo.user@example.com', 'Demo User', true),
  (:legacy_user_id, 'legacy.user@example.com', 'Legacy User', true)
                """
            ),
            {
                "demo_user_id": demo_user_id,
                "legacy_user_id": legacy_user_id,
            },
        )

    _run_upgrade(migration_engine, monkeypatch)

    with migration_engine.begin() as connection:
        app_roles = dict(
            connection.execute(
                text("SELECT email, app_role::text FROM tracker.users ORDER BY email")
            ).all()
        )
        future_role = connection.execute(
            text(
                """
INSERT INTO tracker.users (id, email, full_name, is_active)
VALUES (:future_user_id, 'future.user@example.com', 'Future User', true)
RETURNING app_role::text
                """
            ),
            {"future_user_id": future_user_id},
        ).scalar_one()

    assert app_roles["demo.user@example.com"] == "admin_app"
    assert app_roles["legacy.user@example.com"] == "user"
    assert future_role == "user"


def test_upgrade_converts_legacy_project_roles(migration_engine: Engine, monkeypatch: pytest.MonkeyPatch):
    _prepare_legacy_schema(migration_engine)

    demo_user_id = str(uuid.uuid4())
    project_admin_id = str(uuid.uuid4())
    project_owner_id = str(uuid.uuid4())
    project_member_id = str(uuid.uuid4())
    project_id = str(uuid.uuid4())

    with migration_engine.begin() as connection:
        connection.execute(
            text(
                """
INSERT INTO tracker.users (id, email, full_name, is_active)
VALUES
  (:demo_user_id, 'demo.user@example.com', 'Demo User', true),
  (:project_admin_id, 'legacy.admin@example.com', 'Legacy Admin', true),
  (:project_owner_id, 'legacy.owner@example.com', 'Legacy Owner', true),
  (:project_member_id, 'legacy.member@example.com', 'Legacy Member', true)
                """
            ),
            {
                "demo_user_id": demo_user_id,
                "project_admin_id": project_admin_id,
                "project_owner_id": project_owner_id,
                "project_member_id": project_member_id,
            },
        )
        connection.execute(
            text(
                """
INSERT INTO tracker.projects (id, key, name, created_by)
VALUES (:project_id, 'MIG', 'Migration Project', :demo_user_id)
                """
            ),
            {
                "project_id": project_id,
                "demo_user_id": demo_user_id,
            },
        )
        connection.execute(
            text(
                """
INSERT INTO tracker.project_users (project_id, user_id, role)
VALUES
  (:project_id, :project_admin_id, 'project_admin'),
  (:project_id, :project_owner_id, 'project_owner'),
  (:project_id, :project_member_id, 'project_member')
                """
            ),
            {
                "project_id": project_id,
                "project_admin_id": project_admin_id,
                "project_owner_id": project_owner_id,
                "project_member_id": project_member_id,
            },
        )

    _run_upgrade(migration_engine, monkeypatch)

    with migration_engine.begin() as connection:
        migrated_roles = dict(
            connection.execute(
                text(
                    """
SELECT user_id::text, role::text
FROM tracker.project_users
WHERE project_id = :project_id
ORDER BY user_id::text
                    """
                ),
                {"project_id": project_id},
            ).all()
        )

    assert migrated_roles[project_admin_id] == "admin_project"
    assert migrated_roles[project_owner_id] == "admin_project"
    assert migrated_roles[project_member_id] == "user"
