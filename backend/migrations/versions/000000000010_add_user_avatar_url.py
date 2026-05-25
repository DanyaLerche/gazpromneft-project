"""Add global avatar_url to users."""

from typing import Sequence, Union

from alembic import op


revision: str = "000000000010"
down_revision: Union[str, None] = "000000000009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
SET search_path = tracker, public;

ALTER TABLE users
ADD COLUMN IF NOT EXISTS avatar_url text;
        """
    )


def downgrade() -> None:
    op.execute(
        """
SET search_path = tracker, public;

ALTER TABLE users
DROP COLUMN IF EXISTS avatar_url;
        """
    )
