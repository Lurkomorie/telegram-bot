"""Add shop purchases and mood tracking to chats

Revision ID: 032_add_shop_and_mood
Revises: 031_add_image_cache_indexes
Create Date: 2026-02-01
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '032_add_shop_and_mood'
down_revision = '031_add_image_cache_indexes'
branch_labels = None
depends_on = None


def upgrade():
    # Add mood and coldness_streak columns to chats table
    op.add_column('chats', sa.Column('mood', sa.Integer(), server_default='50', nullable=False))
    op.add_column('chats', sa.Column('coldness_streak', sa.Integer(), server_default='0', nullable=False))
    
    # Create chat_purchases table for tracking shop purchases per chat
    op.create_table(
        'chat_purchases',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('chat_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('chats.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.BigInteger(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('item_key', sa.String(50), nullable=False),  # wine, lipstick, rose, mystery, vibrator, anal_beads
        sa.Column('item_name', sa.String(100), nullable=False),
        sa.Column('price_paid', sa.Integer(), nullable=False),
        sa.Column('mood_boost', sa.Integer(), nullable=False),
        sa.Column('context_effect', sa.Text(), nullable=True),  # Image prompt addition
        sa.Column('purchased_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Index('ix_chat_purchases_chat_id', 'chat_id'),
        sa.Index('ix_chat_purchases_user_id', 'user_id'),
        sa.Index('ix_chat_purchases_item_key', 'item_key'),
    )


def downgrade():
    op.drop_table('chat_purchases')
    op.drop_column('chats', 'coldness_streak')
    op.drop_column('chats', 'mood')
