"""merge system messages migration

Revision ID: 0296caa64d7d
Revises: a38ea596e306, 025
Create Date: 2025-12-01 17:04:24.891648

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0296caa64d7d'
down_revision: Union[str, None] = ('a38ea596e306', '025')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass


