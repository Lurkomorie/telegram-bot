"""add_max_energy_to_users

Revision ID: 396ec01a0a43
Revises: 023
Create Date: 2025-11-25 23:12:19.499354

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '396ec01a0a43'
down_revision: Union[str, None] = '023'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add max_energy column with default value of 100
    op.add_column('users', sa.Column('max_energy', sa.BigInteger(), nullable=False, server_default='100'))


def downgrade() -> None:
    # Remove max_energy column
    op.drop_column('users', 'max_energy')


