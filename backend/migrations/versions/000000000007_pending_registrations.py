"""Store pre-verification signups outside users table."""

from typing import Sequence, Union

from alembic import op


revision: str = "000000000007"
down_revision: Union[str, None] = "000000000006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
SET search_path = tracker, public;

CREATE TABLE IF NOT EXISTS pending_registrations (
  email        varchar(255) PRIMARY KEY,
  full_name    varchar(255) NOT NULL,
  password_hash varchar(255) NOT NULL,
  code_hash    varchar(64) NOT NULL,
  expires_at   timestamptz NOT NULL,
  attempts     integer NOT NULL DEFAULT 0,
  last_sent_at timestamptz NOT NULL,
  created_at   timestamptz NOT NULL DEFAULT now(),
  updated_at   timestamptz NOT NULL DEFAULT now()
);

DO $$
BEGIN
  IF to_regclass('tracker.auth_credentials') IS NOT NULL
     AND to_regclass('tracker.email_verifications') IS NOT NULL THEN
    INSERT INTO pending_registrations (
      email,
      full_name,
      password_hash,
      code_hash,
      expires_at,
      attempts,
      last_sent_at,
      created_at,
      updated_at
    )
    SELECT
      u.email,
      u.full_name,
      ac.password_hash,
      ev.code_hash,
      ev.expires_at,
      ev.attempts,
      ev.last_sent_at,
      ev.created_at,
      ev.updated_at
    FROM users u
    JOIN auth_credentials ac ON ac.user_id = u.id
    JOIN email_verifications ev ON ev.user_id = u.id
    WHERE u.is_email_verified = false
    ON CONFLICT (email) DO UPDATE SET
      full_name = EXCLUDED.full_name,
      password_hash = EXCLUDED.password_hash,
      code_hash = EXCLUDED.code_hash,
      expires_at = EXCLUDED.expires_at,
      attempts = EXCLUDED.attempts,
      last_sent_at = EXCLUDED.last_sent_at,
      updated_at = now();

    DELETE FROM auth_credentials
    WHERE user_id IN (
      SELECT id FROM users WHERE is_email_verified = false
    );

    DELETE FROM email_verifications
    WHERE user_id IN (
      SELECT id FROM users WHERE is_email_verified = false
    );

    DELETE FROM users
    WHERE is_email_verified = false;
  END IF;
END $$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
SET search_path = tracker, public;

DROP TABLE IF EXISTS pending_registrations;
        """
    )

