"""merge heads

Revision ID: a38ea596e306
Revises: 024, 9f3e4c1a2b5d
Create Date: 2025-11-30 23:10:11.125681

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a38ea596e306'
down_revision: Union[str, None] = ('024', '9f3e4c1a2b5d')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass


