"""Add age_verified field to users for age verification

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
    """Add age_verified field to users table"""
    # Add column with default False
    op.add_column('users', sa.Column('age_verified', sa.Boolean, nullable=False, server_default='false'))


def downgrade():
    """Remove age_verified field from users table"""
    op.drop_column('users', 'age_verified')

