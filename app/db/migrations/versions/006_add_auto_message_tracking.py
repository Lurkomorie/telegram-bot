"""Add last_auto_message_at to chats

Revision ID: 006
Revises: 005
Create Date: 2025-10-18

"""
from alembic import op  # pylint: disable=import-error
import sqlalchemy as sa


# revision identifiers, used by Alembic
revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade():
    # Add last_auto_message_at field to chats table for tracking auto-follow-ups
    op.add_column('chats', sa.Column('last_auto_message_at', sa.DateTime(), nullable=True))
    
    print("✅ Added last_auto_message_at field to chats table")


def downgrade():
    # Remove last_auto_message_at field from chats table
    op.drop_column('chats', 'last_auto_message_at')
    
    print("✅ Removed last_auto_message_at field from chats table")




