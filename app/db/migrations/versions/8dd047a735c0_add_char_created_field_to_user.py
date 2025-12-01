"""add_char_created_field_to_user

Revision ID: 8dd047a735c0
Revises: b19568f1a5d7
Create Date: 2025-11-27 23:05:57.568460

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8dd047a735c0'
down_revision: Union[str, None] = 'b19568f1a5d7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add char_created field to users table
    op.add_column('users', sa.Column('char_created', sa.Boolean(), nullable=False, server_default='false'))


def downgrade() -> None:
    # Remove char_created field from users table
    op.drop_column('users', 'char_created')


