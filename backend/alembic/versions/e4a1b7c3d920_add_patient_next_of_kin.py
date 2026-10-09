"""add patient next of kin

Revision ID: e4a1b7c3d920
Revises: c7d2e91a4b58
Create Date: 2026-10-09 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e4a1b7c3d920'
down_revision: Union[str, None] = 'c7d2e91a4b58'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('patients', sa.Column('next_of_kin_name', sa.String(length=200), nullable=True))
    op.add_column('patients', sa.Column('next_of_kin_relationship', sa.String(length=50), nullable=True))
    op.add_column('patients', sa.Column('next_of_kin_phone', sa.String(length=30), nullable=True))
    op.add_column('patients', sa.Column('next_of_kin_address', sa.String(length=300), nullable=True))


def downgrade() -> None:
    op.drop_column('patients', 'next_of_kin_address')
    op.drop_column('patients', 'next_of_kin_phone')
    op.drop_column('patients', 'next_of_kin_relationship')
    op.drop_column('patients', 'next_of_kin_name')
