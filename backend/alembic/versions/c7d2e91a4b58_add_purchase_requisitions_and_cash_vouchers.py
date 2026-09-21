"""add purchase requisitions and cash vouchers

Revision ID: c7d2e91a4b58
Revises: b3a6f2c9e1d4
Create Date: 2026-09-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'c7d2e91a4b58'
down_revision: Union[str, None] = 'b3a6f2c9e1d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NEW_ROLES = ('MEDICAL_SUPERINTENDENT', 'MATRON', 'ACCOUNTS_CLERK')
NEW_ENUM_TYPES = ('requisitionstatus', 'requisitionsignatory', 'cashvoucherstatus')


def _is_postgres() -> bool:
    return op.get_bind().dialect.name == 'postgresql'


def upgrade() -> None:
    if _is_postgres():
        # ADD VALUE can't run inside a transaction block on older Postgres versions.
        with op.get_context().autocommit_block():
            for role in NEW_ROLES:
                op.execute(f"ALTER TYPE roleenum ADD VALUE IF NOT EXISTS '{role}'")
        # The type already exists (created with supplier_payments) — don't try to create it again.
        payment_method = postgresql.ENUM('CASH', 'CARD', 'EFT', 'MEDICAL_AID', name='paymentmethod', create_type=False)
    else:
        payment_method = sa.Enum('CASH', 'CARD', 'EFT', 'MEDICAL_AID', name='paymentmethod')

    op.create_table('purchase_requisitions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('branch_id', sa.Integer(), nullable=False),
    sa.Column('requisition_number', sa.String(length=50), nullable=False),
    sa.Column('department', sa.String(length=100), nullable=False),
    sa.Column('supplier_id', sa.Integer(), nullable=True),
    sa.Column('currency_code', sa.String(length=3), nullable=False),
    sa.Column('status', sa.Enum('PENDING_APPROVAL', 'APPROVED', 'REJECTED', 'ORDERED', 'CANCELLED', name='requisitionstatus'), nullable=False),
    sa.Column('justification', sa.String(length=500), nullable=True),
    sa.Column('total', sa.Numeric(precision=18, scale=2), nullable=False),
    sa.Column('requested_by_id', sa.Integer(), nullable=False),
    sa.Column('rejection_reason', sa.String(length=300), nullable=True),
    sa.Column('purchase_order_id', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['branch_id'], ['branches.id'], ),
    sa.ForeignKeyConstraint(['currency_code'], ['currencies.code'], ),
    sa.ForeignKeyConstraint(['purchase_order_id'], ['purchase_orders.id'], ),
    sa.ForeignKeyConstraint(['requested_by_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('requisition_number')
    )
    op.create_table('purchase_requisition_lines',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('requisition_id', sa.Integer(), nullable=False),
    sa.Column('charge_item_id', sa.Integer(), nullable=False),
    sa.Column('description', sa.String(length=300), nullable=False),
    sa.Column('quantity', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('estimated_unit_cost', sa.Numeric(precision=18, scale=2), nullable=False),
    sa.Column('amount', sa.Numeric(precision=18, scale=2), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['charge_item_id'], ['charge_items.id'], ),
    sa.ForeignKeyConstraint(['requisition_id'], ['purchase_requisitions.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('requisition_signatures',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('requisition_id', sa.Integer(), nullable=False),
    sa.Column('signatory', sa.Enum('MEDICAL_SUPERINTENDENT', 'MATRON', 'ADMIN', name='requisitionsignatory'), nullable=False),
    sa.Column('signed_by_id', sa.Integer(), nullable=False),
    sa.Column('signed_by_name', sa.String(length=200), nullable=False),
    sa.Column('signed_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['requisition_id'], ['purchase_requisitions.id'], ),
    sa.ForeignKeyConstraint(['signed_by_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('requisition_id', 'signatory', name='uq_requisition_signatory')
    )
    op.create_table('cash_vouchers',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('branch_id', sa.Integer(), nullable=False),
    sa.Column('voucher_number', sa.String(length=50), nullable=False),
    sa.Column('purchase_order_id', sa.Integer(), nullable=False),
    sa.Column('method', payment_method, nullable=False),
    sa.Column('currency_code', sa.String(length=3), nullable=False),
    sa.Column('amount', sa.Numeric(precision=18, scale=2), nullable=False),
    sa.Column('description', sa.String(length=300), nullable=True),
    sa.Column('status', sa.Enum('PENDING_CONFIRMATION', 'CONFIRMED', 'DISBURSED', 'REJECTED', 'CANCELLED', name='cashvoucherstatus'), nullable=False),
    sa.Column('prepared_by_id', sa.Integer(), nullable=False),
    sa.Column('rejection_reason', sa.String(length=300), nullable=True),
    sa.Column('accountant_id', sa.Integer(), nullable=True),
    sa.Column('accountant_name', sa.String(length=200), nullable=True),
    sa.Column('accountant_signed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('clerk_id', sa.Integer(), nullable=True),
    sa.Column('clerk_name', sa.String(length=200), nullable=True),
    sa.Column('clerk_signed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('supplier_payment_id', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['accountant_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['branch_id'], ['branches.id'], ),
    sa.ForeignKeyConstraint(['clerk_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['currency_code'], ['currencies.code'], ),
    sa.ForeignKeyConstraint(['prepared_by_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['purchase_order_id'], ['purchase_orders.id'], ),
    sa.ForeignKeyConstraint(['supplier_payment_id'], ['supplier_payments.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('voucher_number')
    )


def downgrade() -> None:
    op.drop_table('cash_vouchers')
    op.drop_table('requisition_signatures')
    op.drop_table('purchase_requisition_lines')
    op.drop_table('purchase_requisitions')
    if _is_postgres():
        for enum_type in NEW_ENUM_TYPES:
            op.execute(f"DROP TYPE IF EXISTS {enum_type}")
    # The new roleenum values are left in place: Postgres can't drop enum values.
