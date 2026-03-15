"""Add bot_id to chats (stub - already applied to production)

Revision ID: 040_add_bot_id_to_chats
Revises: 039_tsundere_starting_mood
Create Date: 2026-03-15
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "040_add_bot_id_to_chats"
down_revision = "039_tsundere_starting_mood"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Already applied to production database.
    pass


def downgrade() -> None:
    pass
