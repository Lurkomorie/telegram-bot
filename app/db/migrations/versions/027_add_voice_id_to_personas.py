"""Add voice_id column to personas table

Revision ID: 027_add_voice_id
Revises: 026_add_missing_user_fields
Create Date: 2024-12-12

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '027_add_voice_id'
down_revision = None  # Will be set by alembic
branch_labels = None
depends_on = None


def upgrade():
    """Add voice_id column to personas table for custom voice selection"""
    op.add_column('personas', sa.Column('voice_id', sa.String(100), nullable=True))


def downgrade():
    """Remove voice_id column from personas table"""
    op.drop_column('personas', 'voice_id')
