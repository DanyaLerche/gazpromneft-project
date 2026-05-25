"""Добавляет таблицы wiki-страниц, ревизий и вложений."""

from typing import Sequence, Union

from alembic import op


revision: str = "000000000004"
down_revision: Union[str, None] = "000000000003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
SET search_path = tracker, public;

CREATE TABLE IF NOT EXISTS wiki_pages (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  parent_id uuid NULL REFERENCES wiki_pages(id) ON DELETE SET NULL,
  title text NOT NULL,
  content_md text NOT NULL DEFAULT '',
  rendered_html text NOT NULL DEFAULT '',
  version integer NOT NULL DEFAULT 1 CHECK (version >= 1),
  created_by uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  updated_by uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_wiki_pages_project_parent
  ON wiki_pages(project_id, parent_id);
CREATE INDEX IF NOT EXISTS idx_wiki_pages_project_updated
  ON wiki_pages(project_id, updated_at);

DO $$ BEGIN
  CREATE TRIGGER trg_wiki_pages_updated_at
  BEFORE UPDATE ON wiki_pages
  FOR EACH ROW
  EXECUTE FUNCTION set_updated_at();
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

CREATE TABLE IF NOT EXISTS wiki_page_revisions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  page_id uuid NOT NULL REFERENCES wiki_pages(id) ON DELETE CASCADE,
  project_id uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  parent_id uuid NULL REFERENCES wiki_pages(id) ON DELETE SET NULL,
  version integer NOT NULL CHECK (version >= 1),
  title text NOT NULL,
  content_md text NOT NULL DEFAULT '',
  rendered_html text NOT NULL DEFAULT '',
  created_by uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (page_id, version)
);

CREATE INDEX IF NOT EXISTS idx_wiki_page_revisions_page_created
  ON wiki_page_revisions(page_id, created_at);

CREATE TABLE IF NOT EXISTS wiki_page_attachments (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  page_id uuid NOT NULL REFERENCES wiki_pages(id) ON DELETE CASCADE,
  uploaded_by uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  file_name text NOT NULL,
  mime_type text NULL,
  size_bytes bigint NOT NULL DEFAULT 0 CHECK (size_bytes >= 0),
  storage_key text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_wiki_page_attachments_page_created
  ON wiki_page_attachments(page_id, created_at);
        """
    )


def downgrade() -> None:
    op.execute(
        """
SET search_path = tracker, public;

DROP INDEX IF EXISTS idx_wiki_page_attachments_page_created;
DROP TABLE IF EXISTS wiki_page_attachments;

DROP INDEX IF EXISTS idx_wiki_page_revisions_page_created;
DROP TABLE IF EXISTS wiki_page_revisions;

DROP TRIGGER IF EXISTS trg_wiki_pages_updated_at ON wiki_pages;
DROP INDEX IF EXISTS idx_wiki_pages_project_updated;
DROP INDEX IF EXISTS idx_wiki_pages_project_parent;
DROP TABLE IF EXISTS wiki_pages;
        """
    )
