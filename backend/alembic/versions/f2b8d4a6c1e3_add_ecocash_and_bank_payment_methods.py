"""add ecocash and bank payment methods

Revision ID: f2b8d4a6c1e3
Revises: e4a1b7c3d920
Create Date: 2026-10-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = 'f2b8d4a6c1e3'
down_revision: Union[str, None] = 'e4a1b7c3d920'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NEW_METHODS = ('ECOCASH', 'BANK')


def upgrade() -> None:
    # SQLite stores the enum as plain VARCHAR, so only Postgres needs the type extended.
    if op.get_bind().dialect.name == 'postgresql':
        # ADD VALUE can't run inside a transaction block on older Postgres versions.
        with op.get_context().autocommit_block():
            for method in NEW_METHODS:
                op.execute(f"ALTER TYPE paymentmethod ADD VALUE IF NOT EXISTS '{method}'")


def downgrade() -> None:
    # Postgres can't drop enum values; leaving them in place is harmless.
    pass
