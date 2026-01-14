"""Add button_name to persona_history_starts and persona_history_translations

Revision ID: add_button_name_hist
Revises: 
Create Date: 2026-01-14

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_button_name_hist'
down_revision = 'add_style_to_personas'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add button_name to persona_history_starts
    op.add_column('persona_history_starts', sa.Column('button_name', sa.String(50), nullable=True))
    
    # Add button_name to persona_history_translations
    op.add_column('persona_history_translations', sa.Column('button_name', sa.String(50), nullable=True))


def downgrade() -> None:
    op.drop_column('persona_history_translations', 'button_name')
    op.drop_column('persona_history_starts', 'button_name')
