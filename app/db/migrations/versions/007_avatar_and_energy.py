"""Add avatar_url and energy fields

Revision ID: 007
Revises: 006
Create Date: 2025-10-22

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade():
    # Add avatar_url to personas table
    op.add_column('personas', sa.Column('avatar_url', sa.Text(), nullable=True))
    
    # Add energy fields to users table
    op.add_column('users', sa.Column('energy', sa.BigInteger(), nullable=False, server_default='100'))
    op.add_column('users', sa.Column('max_energy', sa.BigInteger(), nullable=False, server_default='100'))


def downgrade():
    # Remove energy fields from users
    op.drop_column('users', 'max_energy')
    op.drop_column('users', 'energy')
    
    # Remove avatar_url from personas
    op.drop_column('personas', 'avatar_url')

