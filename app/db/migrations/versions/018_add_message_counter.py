"""Add message counter to chats for image generation decisions

Revision ID: 018
Revises: 017
Create Date: 2025-11-09

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '018'
down_revision = '017'
branch_labels = None
depends_on = None


def upgrade():
    """Add message_count field to chats table"""
    # Add column with default 0
    op.add_column('chats', sa.Column('message_count', sa.BigInteger, nullable=False, server_default='0'))
    
    # Update existing chats to count their messages
    # This SQL counts messages per chat and updates the message_count
    op.execute("""
        UPDATE chats
        SET message_count = (
            SELECT COUNT(*)
            FROM messages
            WHERE messages.chat_id = chats.id
        )
    """)


def downgrade():
    """Remove message_count field from chats table"""
    op.drop_column('chats', 'message_count')

