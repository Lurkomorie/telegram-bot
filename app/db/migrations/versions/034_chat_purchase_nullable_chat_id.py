"""Make ChatPurchase.chat_id nullable with SET NULL on delete

Purchases must survive chat deletion (daily cleanup job).

Revision ID: 034_chat_purchase_nullable_chat_id
Revises: 033_add_persona_starting_mood
Create Date: 2026-02-17
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = '034_chat_purchase_nullable_chat_id'
down_revision = '033_add_persona_starting_mood'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Make column nullable
    op.alter_column('chat_purchases', 'chat_id', existing_type=UUID(), nullable=True)

    # 2. Drop old FK constraint and recreate with ON DELETE SET NULL
    op.drop_constraint('chat_purchases_chat_id_fkey', 'chat_purchases', type_='foreignkey')
    op.create_foreign_key(
        'chat_purchases_chat_id_fkey',
        'chat_purchases',
        'chats',
        ['chat_id'],
        ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    # Revert to CASCADE + NOT NULL (will fail if any NULLs exist)
    op.drop_constraint('chat_purchases_chat_id_fkey', 'chat_purchases', type_='foreignkey')
    op.create_foreign_key(
        'chat_purchases_chat_id_fkey',
        'chat_purchases',
        'chats',
        ['chat_id'],
        ['id'],
        ondelete='CASCADE',
    )
    op.alter_column('chat_purchases', 'chat_id', existing_type=UUID(), nullable=False)
