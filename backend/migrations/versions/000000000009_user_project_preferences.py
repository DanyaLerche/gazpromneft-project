"""Add per-project user preferences for onboarding mode."""

from typing import Sequence, Union

from alembic import op


revision: str = "000000000009"
down_revision: Union[str, None] = "000000000008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
SET search_path = tracker, public;

CREATE TABLE IF NOT EXISTS user_project_preferences (
  id                uuid PRIMARY KEY,
  project_id        uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  user_id           uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  new_employee_mode boolean NOT NULL DEFAULT false,
  created_at        timestamptz NOT NULL DEFAULT now(),
  updated_at        timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_user_project_preferences_project_user
  ON user_project_preferences(project_id, user_id);
        """
    )


def downgrade() -> None:
    op.execute(
        """
SET search_path = tracker, public;

DROP INDEX IF EXISTS idx_user_project_preferences_project_user;
DROP TABLE IF EXISTS user_project_preferences;
        """
    )
