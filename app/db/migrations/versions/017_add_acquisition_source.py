"""Add acquisition source tracking to users

Revision ID: 017
Revises: 016
Create Date: 2025-11-05

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '017'
down_revision = '016'
branch_labels = None
depends_on = None


def upgrade():
    """Add acquisition_source and acquisition_timestamp fields to users table"""
    op.add_column('users', sa.Column('acquisition_source', sa.String(64), nullable=True))
    op.add_column('users', sa.Column('acquisition_timestamp', sa.DateTime, nullable=True))


def downgrade():
    """Remove acquisition tracking fields from users table"""
    op.drop_column('users', 'acquisition_timestamp')
    op.drop_column('users', 'acquisition_source')

