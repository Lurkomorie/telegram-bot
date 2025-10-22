"""Add energy upsell message tracking to users

Revision ID: 009
Revises: 008
Create Date: 2025-10-22

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None


def upgrade():
    # Add energy upsell tracking fields to users table
    op.add_column('users', 
                  sa.Column('last_energy_upsell_message_id', sa.BigInteger(), nullable=True))
    op.add_column('users',
                  sa.Column('last_energy_upsell_chat_id', sa.BigInteger(), nullable=True))


def downgrade():
    # Remove energy upsell tracking fields
    op.drop_column('users', 'last_energy_upsell_chat_id')
    op.drop_column('users', 'last_energy_upsell_message_id')

