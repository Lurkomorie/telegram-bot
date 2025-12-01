"""add_temp_energy_fields

Revision ID: 024
Revises: 023
Create Date: 2025-11-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '024'
down_revision: Union[str, None] = '023'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add temp_energy column with default value of 0
    op.add_column('users', sa.Column('temp_energy', sa.BigInteger(), nullable=False, server_default='0'))
    
    # Add last_temp_energy_refill column (nullable)
    op.add_column('users', sa.Column('last_temp_energy_refill', sa.DateTime(), nullable=True))


def downgrade() -> None:
    # Remove temp_energy and last_temp_energy_refill columns
    op.drop_column('users', 'last_temp_energy_refill')
    op.drop_column('users', 'temp_energy')

