"""Add app roles, migrate project roles, and extend project metadata."""

from typing import Sequence, Union

from alembic import op


revision: str = "000000000005"
down_revision: Union[str, None] = "000000000004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
SET search_path = tracker, public;

DO $$
BEGIN
  CREATE TYPE app_role AS ENUM ('user', 'admin_app');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

ALTER TABLE users
  ADD COLUMN IF NOT EXISTS app_role app_role;

UPDATE users
SET app_role = 'user'
WHERE app_role IS NULL;

UPDATE users
SET app_role = 'admin_app'
WHERE email = 'demo.user@example.com';

ALTER TABLE users
  ALTER COLUMN app_role SET DEFAULT 'user',
  ALTER COLUMN app_role SET NOT NULL;

ALTER TABLE projects
  ADD COLUMN IF NOT EXISTS description text,
  ADD COLUMN IF NOT EXISTS category varchar(50),
  ADD COLUMN IF NOT EXISTS updated_at timestamptz;

UPDATE projects
SET
  description = COALESCE(description, ''),
  category = COALESCE(category, 'Software'),
  updated_at = COALESCE(updated_at, created_at, now())
WHERE description IS NULL
   OR category IS NULL
   OR updated_at IS NULL;

ALTER TABLE projects
  ALTER COLUMN description SET DEFAULT '',
  ALTER COLUMN description SET NOT NULL,
  ALTER COLUMN category SET DEFAULT 'Software',
  ALTER COLUMN category SET NOT NULL,
  ALTER COLUMN updated_at SET DEFAULT now(),
  ALTER COLUMN updated_at SET NOT NULL;

DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM pg_type t
    JOIN pg_namespace n ON n.oid = t.typnamespace
    WHERE t.typname = 'project_role'
      AND n.nspname = 'tracker'
  ) THEN
    CREATE TYPE project_role_new AS ENUM ('user', 'admin_project');

    ALTER TABLE project_users
      ALTER COLUMN role DROP DEFAULT;

    ALTER TABLE project_users
      ALTER COLUMN role TYPE project_role_new
      USING (
        CASE role::text
          WHEN 'project_member' THEN 'user'
          WHEN 'project_admin' THEN 'admin_project'
          WHEN 'project_owner' THEN 'admin_project'
          ELSE 'user'
        END::project_role_new
      );

    DROP TYPE project_role;
    ALTER TYPE project_role_new RENAME TO project_role;
  END IF;
END $$;

ALTER TABLE project_users
  ALTER COLUMN role SET DEFAULT 'user';

DO $$
BEGIN
  CREATE TRIGGER trg_projects_updated_at
  BEFORE UPDATE ON projects
  FOR EACH ROW
  EXECUTE FUNCTION set_updated_at();
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
SET search_path = tracker, public;

DROP TRIGGER IF EXISTS trg_projects_updated_at ON projects;

CREATE TYPE project_role_old AS ENUM ('project_member', 'project_admin', 'project_owner');

ALTER TABLE project_users
  ALTER COLUMN role DROP DEFAULT;

ALTER TABLE project_users
  ALTER COLUMN role TYPE project_role_old
  USING (
    CASE role::text
      WHEN 'user' THEN 'project_member'
      WHEN 'admin_project' THEN 'project_admin'
      ELSE 'project_member'
    END::project_role_old
  );

DROP TYPE project_role;
ALTER TYPE project_role_old RENAME TO project_role;

ALTER TABLE project_users
  ALTER COLUMN role SET DEFAULT 'project_member';

ALTER TABLE projects
  DROP COLUMN IF EXISTS updated_at,
  DROP COLUMN IF EXISTS category,
  DROP COLUMN IF EXISTS description;

ALTER TABLE users
  DROP COLUMN IF EXISTS app_role;

DROP TYPE IF EXISTS app_role;
        """
    )
