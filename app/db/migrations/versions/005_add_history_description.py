"""Add description to persona_history_starts

Revision ID: 005
Revises: 004
Create Date: 2025-10-17

"""
from alembic import op  # pylint: disable=import-error
import sqlalchemy as sa


# revision identifiers, used by Alembic
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade():
    # Add description field to persona_history_starts table
    op.add_column('persona_history_starts', sa.Column('description', sa.Text(), nullable=True))
    
    print("✅ Added description field to persona_history_starts table")


def downgrade():
    # Remove description field from persona_history_starts table
    op.drop_column('persona_history_starts', 'description')
    
    print("✅ Removed description field from persona_history_starts table")


