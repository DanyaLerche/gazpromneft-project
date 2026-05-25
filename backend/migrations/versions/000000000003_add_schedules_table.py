"""Добавляет таблицу schedules и индекс по пользователю/дате."""

from typing import Sequence, Union

from alembic import op


revision: str = "000000000003"
down_revision: Union[str, None] = "000000000002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
SET search_path = tracker, public;

CREATE TABLE IF NOT EXISTS schedules (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id),
  date date NOT NULL,
  planned_hours numeric NULL,
  comment text NULL
);

CREATE INDEX IF NOT EXISTS idx_schedules_user_date
  ON schedules(user_id, date);
        """
    )


def downgrade() -> None:
    op.execute(
        """
SET search_path = tracker, public;

DROP INDEX IF EXISTS idx_schedules_user_date;
DROP TABLE IF EXISTS schedules;
        """
    )
