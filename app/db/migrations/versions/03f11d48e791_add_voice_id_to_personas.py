"""add_voice_id_to_personas

Revision ID: 03f11d48e791
Revises: 026
Create Date: 2025-12-13 22:56:24.820767

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '03f11d48e791'
down_revision: Union[str, None] = '026'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add voice_id column to personas table for custom voice selection"""
    # Using execute to handle IF NOT EXISTS (in case column was added manually)
    op.execute("""
        ALTER TABLE personas 
        ADD COLUMN IF NOT EXISTS voice_id VARCHAR(100)
    """)


def downgrade() -> None:
    """Remove voice_id column from personas table"""
    op.drop_column('personas', 'voice_id')


