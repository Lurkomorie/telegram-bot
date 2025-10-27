"""Add status field to chats

Revision ID: 014
Revises: 013
Create Date: 2025-10-25
"""
from alembic import op
import sqlalchemy as sa

# Revision identifiers
revision = '014'
down_revision = '013'
branch_labels = None
depends_on = None


def upgrade():
    """Add status column to chats table"""
    # Add status column with default 'active'
    op.add_column('chats', 
        sa.Column('status', sa.String(20), nullable=False, server_default='active')
    )
    
    # Add check constraint for valid status values
    op.create_check_constraint(
        'chats_status_check',
        'chats',
        "status IN ('active', 'archived')"
    )
    
    # Add index on status for efficient scheduler queries
    op.create_index('ix_chats_status', 'chats', ['status'])
    
    # Set all existing chats to 'active' (already handled by server_default, but being explicit)
    op.execute("UPDATE chats SET status = 'active' WHERE status IS NULL")


def downgrade():
    """Remove status column from chats table"""
    op.drop_index('ix_chats_status', table_name='chats')
    op.drop_constraint('chats_status_check', 'chats', type_='check')
    op.drop_column('chats', 'status')

