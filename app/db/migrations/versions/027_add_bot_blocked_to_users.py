"""add_bot_blocked_to_users

Revision ID: 027
Revises: 03f11d48e791
Create Date: 2025-12-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '027'
down_revision: Union[str, None] = '03f11d48e791'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add bot_blocked field to users table
    op.add_column('users', sa.Column('bot_blocked', sa.Boolean(), nullable=False, server_default='false'))
    # Add bot_blocked_at field to users table
    op.add_column('users', sa.Column('bot_blocked_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    # Remove bot_blocked_at field from users table
    op.drop_column('users', 'bot_blocked_at')
    # Remove bot_blocked field from users table
    op.drop_column('users', 'bot_blocked')

