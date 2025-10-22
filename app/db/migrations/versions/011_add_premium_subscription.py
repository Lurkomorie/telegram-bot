"""Add premium subscription to users

Revision ID: 011
Revises: 010
Create Date: 2025-10-22

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '011'
down_revision = '010'
branch_labels = None
depends_on = None


def upgrade():
    # Add premium subscription fields to users table
    op.add_column('users', 
                  sa.Column('is_premium', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('users',
                  sa.Column('premium_until', sa.DateTime(), nullable=True))


def downgrade():
    # Remove premium subscription fields
    op.drop_column('users', 'premium_until')
    op.drop_column('users', 'is_premium')

