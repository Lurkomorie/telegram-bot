"""Add missing user fields (temp_energy, last_temp_energy_refill, char_created)

This migration adds fields that should have been added by earlier migrations
but were missing in production due to migration version conflicts.

Revision ID: 026
Revises: 0296caa64d7d
Create Date: 2025-12-01

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = '026'
down_revision = '0296caa64d7d'
branch_labels = None
depends_on = None


def upgrade():
    """Add missing fields only if they don't exist"""
    connection = op.get_bind()
    
    # Check and add temp_energy if not exists
    result = connection.execute(text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name='users' AND column_name='temp_energy'"
    ))
    if not result.fetchone():
        op.add_column('users', sa.Column('temp_energy', sa.BigInteger(), nullable=False, server_default='0'))
        print("✅ Added temp_energy column")
    else:
        print("⏭️  temp_energy already exists, skipping")
    
    # Check and add last_temp_energy_refill if not exists
    result = connection.execute(text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name='users' AND column_name='last_temp_energy_refill'"
    ))
    if not result.fetchone():
        op.add_column('users', sa.Column('last_temp_energy_refill', sa.DateTime(), nullable=True))
        print("✅ Added last_temp_energy_refill column")
    else:
        print("⏭️  last_temp_energy_refill already exists, skipping")
    
    # Check and add char_created if not exists
    result = connection.execute(text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name='users' AND column_name='char_created'"
    ))
    if not result.fetchone():
        op.add_column('users', sa.Column('char_created', sa.Boolean(), nullable=False, server_default='false'))
        print("✅ Added char_created column")
    else:
        print("⏭️  char_created already exists, skipping")


def downgrade():
    """Remove the added fields"""
    # Only drop if exists
    connection = op.get_bind()
    
    result = connection.execute(text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name='users' AND column_name='char_created'"
    ))
    if result.fetchone():
        op.drop_column('users', 'char_created')
    
    result = connection.execute(text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name='users' AND column_name='last_temp_energy_refill'"
    ))
    if result.fetchone():
        op.drop_column('users', 'last_temp_energy_refill')
    
    result = connection.execute(text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name='users' AND column_name='temp_energy'"
    ))
    if result.fetchone():
        op.drop_column('users', 'temp_energy')

