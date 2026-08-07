"""Add cryptopay_invoice_id column to payment_transactions

Revision ID: 041_add_cryptopay_invoice_id
Revises: 040_add_bot_id_to_chats
Create Date: 2026-03-11
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '041_add_cryptopay_invoice_id'
down_revision = '040_add_bot_id_to_chats'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('payment_transactions', sa.Column('cryptopay_invoice_id', sa.String(255), nullable=True))
    op.create_index('ix_payment_transactions_cryptopay_invoice_id', 'payment_transactions', ['cryptopay_invoice_id'])


def downgrade() -> None:
    op.drop_index('ix_payment_transactions_cryptopay_invoice_id', table_name='payment_transactions')
    op.drop_column('payment_transactions', 'cryptopay_invoice_id')
