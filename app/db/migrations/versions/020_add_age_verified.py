"""Add age_verified field to users for age verification

Revision ID: 020
Revises: 019
Create Date: 2025-11-10

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '020'
down_revision = '019'
branch_labels = None
depends_on = None


def upgrade():
    """Add age_verified field to users table"""
    # Add column with default False
    op.add_column('users', sa.Column('age_verified', sa.Boolean, nullable=False, server_default='false'))


def downgrade():
    """Remove age_verified field from users table"""
    op.drop_column('users', 'age_verified')

