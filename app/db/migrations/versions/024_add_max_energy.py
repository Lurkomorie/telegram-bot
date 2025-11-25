"""Add max_energy column to users

Revision ID: 024
Revises: d97e2ee04e72
Create Date: 2025-11-25

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '024'
down_revision = 'd97e2ee04e72'
branch_labels = None
depends_on = None


def upgrade():
    # Add max_energy column to users table if it doesn't exist
    # Using server_default to set default value for existing rows
    op.add_column('users', sa.Column('max_energy', sa.BigInteger(), nullable=False, server_default='100'))


def downgrade():
    # Remove max_energy column from users
    op.drop_column('users', 'max_energy')

