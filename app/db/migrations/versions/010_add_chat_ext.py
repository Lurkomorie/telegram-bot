"""Add ext column to chats table

Revision ID: 010
Revises: 009
Create Date: 2025-10-22

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '010'
down_revision = '009'
branch_labels = None
depends_on = None


def upgrade():
    # Add ext column to chats table
    op.add_column('chats', 
                  sa.Column('ext', postgresql.JSONB(astext_type=sa.Text()), 
                           nullable=True, server_default=sa.text("'{}'::jsonb")))


def downgrade():
    # Remove ext column from chats table
    op.drop_column('chats', 'ext')

