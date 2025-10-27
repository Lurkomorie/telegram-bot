"""add image_prompt to persona_history_starts

Revision ID: 013
Revises: 012
Create Date: 2025-10-24
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '013'
down_revision = '012'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add image_prompt column to persona_history_starts
    op.add_column('persona_history_starts', sa.Column('image_prompt', sa.Text(), nullable=True))


def downgrade() -> None:
    # Remove image_prompt column from persona_history_starts
    op.drop_column('persona_history_starts', 'image_prompt')

