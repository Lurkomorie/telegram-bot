"""Add wide_menu_image_url to PersonaHistoryStart

Revision ID: 008
Revises: 007
Create Date: 2025-10-22

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None


def upgrade():
    # Add wide_menu_image_url to persona_history_starts table
    op.add_column('persona_history_starts', 
                  sa.Column('wide_menu_image_url', sa.Text(), nullable=True))


def downgrade():
    # Remove wide_menu_image_url from persona_history_starts
    op.drop_column('persona_history_starts', 'wide_menu_image_url')

