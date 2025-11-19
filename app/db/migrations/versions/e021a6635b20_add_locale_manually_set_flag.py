"""add_locale_manually_set_flag

Revision ID: e021a6635b20
Revises: 273689a11086
Create Date: 2025-11-19 10:31:54.456488

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e021a6635b20'
down_revision: Union[str, None] = '273689a11086'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add locale_manually_set column to users table
    op.add_column('users', sa.Column('locale_manually_set', sa.Boolean(), nullable=False, server_default='false'))


def downgrade() -> None:
    # Remove locale_manually_set column from users table
    op.drop_column('users', 'locale_manually_set')


