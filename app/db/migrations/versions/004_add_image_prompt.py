"""Add image_prompt to personas

Revision ID: 004
Revises: 003
Create Date: 2025-10-17

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade():
    # Add image_prompt field to personas table
    op.add_column('personas', sa.Column('image_prompt', sa.Text(), nullable=True))
    
    print("✅ Added image_prompt field to personas table")


def downgrade():
    # Remove image_prompt field from personas table
    op.drop_column('personas', 'image_prompt')
    
    print("✅ Removed image_prompt field from personas table")


