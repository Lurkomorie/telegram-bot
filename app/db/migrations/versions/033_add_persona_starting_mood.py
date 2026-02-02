"""Add starting_mood to personas

Revision ID: 033_add_persona_starting_mood
Revises: 032_add_shop_and_mood
Create Date: 2026-02-02
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '033_add_persona_starting_mood'
down_revision = '032_add_shop_and_mood'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add starting_mood column to personas table
    op.add_column('personas', sa.Column('starting_mood', sa.Integer(), nullable=True, server_default='50'))
    
    # Set starting mood for existing public personas based on their personality
    # These can be adjusted later via admin
    op.execute("""
        UPDATE personas 
        SET starting_mood = 50 
        WHERE starting_mood IS NULL
    """)


def downgrade() -> None:
    op.drop_column('personas', 'starting_mood')
