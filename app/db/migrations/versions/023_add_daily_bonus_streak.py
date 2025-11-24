"""add daily bonus streak

Revision ID: 023
Revises: 022
Create Date: 2024-11-24

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '023'
down_revision = '022'
branch_labels = None
depends_on = None


def upgrade():
    # Add daily_bonus_streak column to users table
    op.add_column('users', sa.Column('daily_bonus_streak', sa.BigInteger(), server_default='0', nullable=False))


def downgrade():
    # Remove daily_bonus_streak column
    op.drop_column('users', 'daily_bonus_streak')

