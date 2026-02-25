"""Reduce new-user default energy to 50

Revision ID: 036_reduce_new_user_energy_to_50
Revises: 035_cache_lookup_fileid
Create Date: 2026-02-25
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "036_reduce_new_user_energy_to_50"
down_revision = "035_cache_lookup_fileid"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # New users should start with 50 energy/tokens.
    op.alter_column(
        "users",
        "energy",
        existing_type=sa.BigInteger(),
        server_default="50",
        existing_nullable=False,
    )
    op.alter_column(
        "users",
        "max_energy",
        existing_type=sa.BigInteger(),
        server_default="50",
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "users",
        "energy",
        existing_type=sa.BigInteger(),
        server_default="80",
        existing_nullable=False,
    )
    op.alter_column(
        "users",
        "max_energy",
        existing_type=sa.BigInteger(),
        server_default="80",
        existing_nullable=False,
    )
