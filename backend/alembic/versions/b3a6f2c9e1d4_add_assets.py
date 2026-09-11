"""add assets

Revision ID: b3a6f2c9e1d4
Revises: df1512f577e7
Create Date: 2026-09-11 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b3a6f2c9e1d4'
down_revision: Union[str, None] = 'df1512f577e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('assets',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('branch_id', sa.Integer(), nullable=False),
    sa.Column('asset_code', sa.String(length=30), nullable=False),
    sa.Column('asset_name', sa.String(length=200), nullable=False),
    sa.Column('department', sa.String(length=100), nullable=False),
    sa.Column('acquisition_date', sa.Date(), nullable=False),
    sa.Column('cost', sa.Numeric(precision=18, scale=2), nullable=False),
    sa.Column('currency_code', sa.String(length=3), nullable=False),
    sa.Column('netbook_value', sa.Numeric(precision=18, scale=2), nullable=False),
    sa.Column('status', sa.Enum('ACTIVE', 'DISPOSED', name='assetstatus'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['branch_id'], ['branches.id'], ),
    sa.ForeignKeyConstraint(['currency_code'], ['currencies.code'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('asset_code')
    )


def downgrade() -> None:
    op.drop_table('assets')
