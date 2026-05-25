"""Add DB cache for onboarding recommendations."""

from typing import Sequence, Union

from alembic import op


revision: str = "000000000008"
down_revision: Union[str, None] = "000000000007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
SET search_path = tracker, public;

CREATE TABLE IF NOT EXISTS onboarding_recommendation_snapshots (
  id           uuid PRIMARY KEY,
  project_id   uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  user_id      uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  payload      jsonb NOT NULL,
  generated_at timestamptz NOT NULL DEFAULT now(),
  expires_at   timestamptz NOT NULL,
  created_at   timestamptz NOT NULL DEFAULT now(),
  updated_at   timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_onboarding_snapshot_project_user
  ON onboarding_recommendation_snapshots(project_id, user_id);

CREATE INDEX IF NOT EXISTS idx_onboarding_snapshot_expires_at
  ON onboarding_recommendation_snapshots(expires_at);
        """
    )


def downgrade() -> None:
    op.execute(
        """
SET search_path = tracker, public;

DROP INDEX IF EXISTS idx_onboarding_snapshot_expires_at;
DROP INDEX IF EXISTS idx_onboarding_snapshot_project_user;
DROP TABLE IF EXISTS onboarding_recommendation_snapshots;
        """
    )
