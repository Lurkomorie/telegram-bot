"""merge_energy_and_button_name_heads

Revision ID: 832ab5755258
Revises: 029_reduce_max_energy_to_80, add_button_name_hist
Create Date: 2026-01-22 14:15:09.716230

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '832ab5755258'
down_revision: Union[str, None] = ('029_reduce_max_energy_to_80', 'add_button_name_hist')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass


