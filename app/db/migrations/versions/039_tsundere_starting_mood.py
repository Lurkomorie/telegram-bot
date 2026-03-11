"""Set tsundere persona starting mood

Revision ID: 039_tsundere_starting_mood
Revises: 036_reduce_new_user_energy_to_50
Create Date: 2026-03-01
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "039_tsundere_starting_mood"
down_revision = "036_reduce_new_user_energy_to_50"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Already applied to production database.
    pass


def downgrade() -> None:
    pass
