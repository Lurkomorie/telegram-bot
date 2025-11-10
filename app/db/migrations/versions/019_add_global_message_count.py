"""Add global_message_count to users for priority queue

Revision ID: 019
Revises: 018
Create Date: 2025-11-10

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '019'
down_revision = '018'
branch_labels = None
depends_on = None


def upgrade():
    """Add global_message_count field to users table"""
    # Add column with default 0
    op.add_column('users', sa.Column('global_message_count', sa.BigInteger, nullable=False, server_default='0'))
    
    # Backfill existing users by counting their messages across all chats
    # This SQL counts all user messages (role='user') for each user
    op.execute("""
        UPDATE users
        SET global_message_count = (
            SELECT COUNT(*)
            FROM messages m
            JOIN chats c ON m.chat_id = c.id
            WHERE c.user_id = users.id AND m.role = 'user'
        )
    """)


def downgrade():
    """Remove global_message_count field from users table"""
    op.drop_column('users', 'global_message_count')

