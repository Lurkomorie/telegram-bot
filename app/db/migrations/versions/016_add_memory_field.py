"""Add memory field to chats

Revision ID: 016
Revises: 015
Create Date: 2025-10-29

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '016'
down_revision = '015'
branch_labels = None
depends_on = None


def upgrade():
    """Add memory column to chats table"""
    op.add_column('chats', sa.Column('memory', sa.Text, nullable=True))


def downgrade():
    """Remove memory column from chats table"""
    op.drop_column('chats', 'memory')

