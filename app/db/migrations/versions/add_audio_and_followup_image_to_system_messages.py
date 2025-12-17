"""Add audio_url and followup_image_url to system messages

Revision ID: c7a3e9f12b4d
Revises: b19568f1a5d7
Create Date: 2025-12-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7a3e9f12b4d'
down_revision: Union[str, None] = '027'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add audio_url and followup_image_url columns to system_messages and system_message_templates"""
    # Add to system_messages table
    op.add_column('system_messages', sa.Column('audio_url', sa.Text(), nullable=True))
    op.add_column('system_messages', sa.Column('followup_image_url', sa.Text(), nullable=True))
    
    # Add to system_message_templates table
    op.add_column('system_message_templates', sa.Column('audio_url', sa.Text(), nullable=True))
    op.add_column('system_message_templates', sa.Column('followup_image_url', sa.Text(), nullable=True))


def downgrade() -> None:
    """Remove audio_url and followup_image_url columns"""
    # Remove from system_messages table
    op.drop_column('system_messages', 'followup_image_url')
    op.drop_column('system_messages', 'audio_url')
    
    # Remove from system_message_templates table
    op.drop_column('system_message_templates', 'followup_image_url')
    op.drop_column('system_message_templates', 'audio_url')
