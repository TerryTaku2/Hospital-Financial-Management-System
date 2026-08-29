"""make invoice line charge item optional

Revision ID: 5eed475c69c8
Revises: c80f90df074a
Create Date: 2026-08-29 14:58:00.963889

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '5eed475c69c8'
down_revision: Union[str, None] = 'c80f90df074a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('invoice_lines') as batch_op:
        batch_op.alter_column('charge_item_id', existing_type=sa.INTEGER(), nullable=True)


def downgrade() -> None:
    with op.batch_alter_table('invoice_lines') as batch_op:
        batch_op.alter_column('charge_item_id', existing_type=sa.INTEGER(), nullable=False)
