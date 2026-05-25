"""Initial schema created from backend/db/init.sql.

- схема tracker
- enum-типы
- функция set_updated_at и триггеры
- основные таблицы и индексы
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "000000000001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Содержимое перенесено из backend/db/init.sql
    op.execute(
        """
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE SCHEMA IF NOT EXISTS tracker;
SET search_path = tracker, public;

DO $$ BEGIN
  CREATE TYPE issue_type AS ENUM ('epic', 'task');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE status_category AS ENUM ('todo', 'in_progress', 'done');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE notification_scope AS ENUM ('ALL', 'CREATE_AND_RESOLVE', 'NONE');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE notification_channel AS ENUM ('in_app', 'email');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE notification_event_type AS ENUM ('created', 'updated', 'commented', 'resolved', 'reopened');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE project_role AS ENUM ('project_member', 'project_admin', 'project_owner');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at := now();
  RETURN NEW;
END;
$$;

CREATE TABLE IF NOT EXISTS users (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  email      text NOT NULL UNIQUE,
  full_name  text NOT NULL,
  is_active  boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS projects (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  key         text NOT NULL UNIQUE,
  name        text NOT NULL,
  created_by  uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS project_users (
  project_id uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  user_id    uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role       project_role NOT NULL DEFAULT 'project_member',
  joined_at  timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (project_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_project_users_user ON project_users(user_id);

CREATE TABLE IF NOT EXISTS statuses (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  name       text NOT NULL,
  category   status_category NOT NULL DEFAULT 'todo',
  sort_order integer NOT NULL DEFAULT 0,
  UNIQUE (project_id, name)
);

CREATE INDEX IF NOT EXISTS idx_statuses_project_sort ON statuses(project_id, sort_order);

CREATE TABLE IF NOT EXISTS criticalities (
  id     uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name   text NOT NULL UNIQUE,
  level  integer NOT NULL UNIQUE
);

INSERT INTO criticalities (name, level) VALUES
  ('Lowest', 1),
  ('Low', 2),
  ('Medium', 3),
  ('High', 4),
  ('Highest', 5)
ON CONFLICT DO NOTHING;

CREATE TABLE IF NOT EXISTS issues (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id      uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

  key             text NOT NULL,
  type            issue_type NOT NULL,

  title           text NOT NULL,
  description     text,

  criticality_id  uuid NULL REFERENCES criticalities(id) ON DELETE SET NULL,
  status_id       uuid NULL REFERENCES statuses(id) ON DELETE RESTRICT,

  author_id       uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  assignee_id     uuid NULL REFERENCES users(id) ON DELETE SET NULL,

  parent_id       uuid NULL REFERENCES issues(id) ON DELETE SET NULL,
  start_date      date NULL,
  due_date        date NULL,
  taken_in_work_at timestamptz NULL,
  resolved_at     timestamptz NULL,
  planned_hours   numeric(10,2) NULL CHECK (planned_hours IS NULL OR planned_hours >= 0),

  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now(),

  UNIQUE (project_id, key)
);

CREATE INDEX IF NOT EXISTS idx_issues_project_type ON issues(project_id, type);
CREATE INDEX IF NOT EXISTS idx_issues_project_status ON issues(project_id, status_id);
CREATE INDEX IF NOT EXISTS idx_issues_assignee ON issues(assignee_id);
CREATE INDEX IF NOT EXISTS idx_issues_parent ON issues(parent_id);
CREATE INDEX IF NOT EXISTS idx_issues_created_at ON issues(created_at);
CREATE INDEX IF NOT EXISTS idx_issues_taken_in_work_at ON issues(taken_in_work_at);
CREATE INDEX IF NOT EXISTS idx_issues_resolved_at ON issues(resolved_at);

DO $$ BEGIN
  CREATE TRIGGER trg_issues_updated_at
  BEFORE UPDATE ON issues
  FOR EACH ROW
  EXECUTE FUNCTION set_updated_at();
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

CREATE TABLE IF NOT EXISTS issue_links (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id  uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

  source_id   uuid NOT NULL REFERENCES issues(id) ON DELETE CASCADE,
  target_id   uuid NOT NULL REFERENCES issues(id) ON DELETE CASCADE,

  link_type   text NOT NULL,

  created_by  uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  created_at  timestamptz NOT NULL DEFAULT now(),

  CHECK (source_id <> target_id),
  UNIQUE (source_id, target_id, link_type)
);

CREATE INDEX IF NOT EXISTS idx_issue_links_source ON issue_links(source_id);
CREATE INDEX IF NOT EXISTS idx_issue_links_target ON issue_links(target_id);
CREATE INDEX IF NOT EXISTS idx_issue_links_project ON issue_links(project_id);

CREATE TABLE IF NOT EXISTS issue_watchers (
  issue_id   uuid NOT NULL REFERENCES issues(id) ON DELETE CASCADE,
  user_id    uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (issue_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_issue_watchers_user ON issue_watchers(user_id);

CREATE TABLE IF NOT EXISTS issue_comments (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  issue_id   uuid NOT NULL REFERENCES issues(id) ON DELETE CASCADE,
  author_id  uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  body       text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_issue_comments_issue_created ON issue_comments(issue_id, created_at);

DO $$ BEGIN
  CREATE TRIGGER trg_issue_comments_updated_at
  BEFORE UPDATE ON issue_comments
  FOR EACH ROW
  EXECUTE FUNCTION set_updated_at();
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

CREATE TABLE IF NOT EXISTS issue_attachments (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  issue_id    uuid NOT NULL REFERENCES issues(id) ON DELETE CASCADE,
  uploaded_by uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  file_name   text NOT NULL,
  mime_type   text NULL,
  size_bytes  bigint NOT NULL DEFAULT 0 CHECK (size_bytes >= 0),
  storage_key text NOT NULL,
  created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_issue_attachments_issue_created ON issue_attachments(issue_id, created_at);

CREATE TABLE IF NOT EXISTS worklogs (
  id        uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  issue_id  uuid NOT NULL REFERENCES issues(id) ON DELETE CASCADE,
  user_id   uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,

  work_date date NOT NULL,
  hours     numeric(10,2) NOT NULL CHECK (hours > 0),

  comment   text NULL,

  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_worklogs_issue_date ON worklogs(issue_id, work_date);
CREATE INDEX IF NOT EXISTS idx_worklogs_user_date ON worklogs(user_id, work_date);

DO $$ BEGIN
  CREATE TRIGGER trg_worklogs_updated_at
  BEFORE UPDATE ON worklogs
  FOR EACH ROW
  EXECUTE FUNCTION set_updated_at();
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

CREATE TABLE IF NOT EXISTS notification_settings (
  user_id    uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  project_id uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  scope      notification_scope NOT NULL DEFAULT 'ALL',
  PRIMARY KEY (user_id, project_id)
);

CREATE TABLE IF NOT EXISTS notification_events (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  issue_id    uuid NOT NULL REFERENCES issues(id) ON DELETE CASCADE,
  event_type  notification_event_type NOT NULL,
  actor_id    uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_notification_events_issue_time ON notification_events(issue_id, created_at);

CREATE TABLE IF NOT EXISTS user_notifications (
  user_id   uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  event_id  uuid NOT NULL REFERENCES notification_events(id) ON DELETE CASCADE,
  channel   notification_channel NOT NULL DEFAULT 'in_app',
  is_read   boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, event_id, channel)
);

CREATE INDEX IF NOT EXISTS idx_user_notifications_user_read ON user_notifications(user_id, is_read, created_at);

CREATE TABLE IF NOT EXISTS dashboards (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  owner_id   uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name       text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (project_id, owner_id, name)
);

CREATE TABLE IF NOT EXISTS dashboard_widgets (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  dashboard_id uuid NOT NULL REFERENCES dashboards(id) ON DELETE CASCADE,
  widget_type  text NOT NULL,
  config_json  jsonb NOT NULL DEFAULT '{}'::jsonb,
  sort_order   integer NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_dashboard_widgets_dash_sort ON dashboard_widgets(dashboard_id, sort_order);
"""
    )


def downgrade() -> None:
    # Полный откат схемы tracker вместе с версиями Alembic.
    op.execute("DROP SCHEMA IF EXISTS tracker CASCADE;")

