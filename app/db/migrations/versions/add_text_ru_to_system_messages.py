"""Add text_ru column to system_messages table

Revision ID: add_text_ru_col
Revises: 
Create Date: 2024-12-23

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_text_ru_col'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Add text_ru column for Russian version of system messages"""
    op.add_column('system_messages', sa.Column('text_ru', sa.Text(), nullable=True))


def downgrade():
    """Remove text_ru column"""
    op.drop_column('system_messages', 'text_ru')

