"""Add payment_provider, amount_rub, paritypay_invoice_id to payment_transactions

These columns exist in the ORM model (PaymentTransaction) but were only ever
added by hand on the dev database, never via a migration. On any database
without them the ORM emits SELECTs for columns that don't exist and every
query on payment_transactions fails. This migration adds them idempotently,
so it is a no-op where a hand-applied column already exists.

Revision ID: 042_add_payment_provider_columns
Revises: 041_add_cryptopay_invoice_id
Create Date: 2026-08-08
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '042_add_payment_provider_columns'
down_revision = '041_add_cryptopay_invoice_id'
branch_labels = None
depends_on = None

TABLE = 'payment_transactions'


def _existing_columns(bind) -> set:
    inspector = sa.inspect(bind)
    return {col['name'] for col in inspector.get_columns(TABLE)}


def upgrade() -> None:
    bind = op.get_bind()
    existing = _existing_columns(bind)

    if 'payment_provider' not in existing:
        # NOT NULL with a server default so existing rows backfill cleanly.
        op.add_column(TABLE, sa.Column(
            'payment_provider', sa.String(30),
            nullable=False, server_default='telegram_stars',
        ))

    if 'amount_rub' not in existing:
        op.add_column(TABLE, sa.Column('amount_rub', sa.Numeric(), nullable=True))

    if 'paritypay_invoice_id' not in existing:
        op.add_column(TABLE, sa.Column('paritypay_invoice_id', sa.String(255), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    existing = _existing_columns(bind)
    if 'paritypay_invoice_id' in existing:
        op.drop_column(TABLE, 'paritypay_invoice_id')
    if 'amount_rub' in existing:
        op.drop_column(TABLE, 'amount_rub')
    if 'payment_provider' in existing:
        op.drop_column(TABLE, 'payment_provider')
