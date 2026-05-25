"""Add email verification support for auth registration flow."""

from typing import Sequence, Union

from alembic import op


revision: str = "000000000006"
down_revision: Union[str, None] = "000000000005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
SET search_path = tracker, public;

ALTER TABLE users
  ADD COLUMN IF NOT EXISTS is_email_verified boolean;

UPDATE users
SET is_email_verified = true
WHERE is_email_verified IS NULL;

ALTER TABLE users
  ALTER COLUMN is_email_verified SET DEFAULT false,
  ALTER COLUMN is_email_verified SET NOT NULL;

CREATE TABLE IF NOT EXISTS email_verifications (
  user_id      uuid PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  code_hash    varchar(64) NOT NULL,
  expires_at   timestamptz NOT NULL,
  attempts     integer NOT NULL DEFAULT 0,
  last_sent_at timestamptz NOT NULL,
  created_at   timestamptz NOT NULL DEFAULT now(),
  updated_at   timestamptz NOT NULL DEFAULT now()
);
        """
    )


def downgrade() -> None:
    op.execute(
        """
SET search_path = tracker, public;

DROP TABLE IF EXISTS email_verifications;

ALTER TABLE users
  DROP COLUMN IF EXISTS is_email_verified;
        """
    )

