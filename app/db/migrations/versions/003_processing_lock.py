"""Add processing lock to chats

Revision ID: 003
Revises: 002
Create Date: 2025-10-16

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade():
    # Add processing lock fields to chats table
    op.add_column('chats', sa.Column('is_processing', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('chats', sa.Column('processing_started_at', sa.DateTime(), nullable=True))
    
    print("✅ Added processing lock fields to chats table")


def downgrade():
    # Remove processing lock fields from chats table
    op.drop_column('chats', 'processing_started_at')
    op.drop_column('chats', 'is_processing')
    
    print("✅ Removed processing lock fields from chats table")


