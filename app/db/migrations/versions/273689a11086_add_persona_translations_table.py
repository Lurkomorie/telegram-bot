"""add_persona_translations_table

Revision ID: 273689a11086
Revises: 214aa12f574a
Create Date: 2025-11-18 18:33:53.794683

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = '273689a11086'
down_revision: Union[str, None] = '214aa12f574a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create persona_translations table for persona descriptions
    op.create_table(
        'persona_translations',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('persona_id', UUID(as_uuid=True), sa.ForeignKey('personas.id', ondelete='CASCADE'), nullable=False),
        sa.Column('language', sa.String(10), nullable=False),  # 'en', 'ru', 'fr', 'de', 'es'
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('small_description', sa.Text(), nullable=True),
        sa.Column('intro', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('NOW()'), onupdate=sa.text('NOW()'), nullable=True),
        sa.UniqueConstraint('persona_id', 'language', name='uq_persona_translations_persona_language')
    )
    
    # Create indexes for efficient lookups
    op.create_index('ix_persona_translations_persona_id', 'persona_translations', ['persona_id'])
    op.create_index('ix_persona_translations_language', 'persona_translations', ['language'])
    
    # Create persona_history_translations table for story descriptions
    op.create_table(
        'persona_history_translations',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('history_id', UUID(as_uuid=True), sa.ForeignKey('persona_history_starts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('language', sa.String(10), nullable=False),  # 'en', 'ru', 'fr', 'de', 'es'
        sa.Column('name', sa.String(255), nullable=True),  # Story name
        sa.Column('small_description', sa.Text(), nullable=True),  # Short story description
        sa.Column('description', sa.Text(), nullable=True),  # Scene-setting description
        sa.Column('text', sa.Text(), nullable=True),  # Greeting message
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('NOW()'), onupdate=sa.text('NOW()'), nullable=True),
        sa.UniqueConstraint('history_id', 'language', name='uq_persona_history_translations_history_language')
    )
    
    # Create indexes for efficient lookups
    op.create_index('ix_persona_history_translations_history_id', 'persona_history_translations', ['history_id'])
    op.create_index('ix_persona_history_translations_language', 'persona_history_translations', ['language'])


def downgrade() -> None:
    # Drop persona_history_translations table
    op.drop_index('ix_persona_history_translations_language', table_name='persona_history_translations')
    op.drop_index('ix_persona_history_translations_history_id', table_name='persona_history_translations')
    op.drop_table('persona_history_translations')
    
    # Drop persona_translations table
    op.drop_index('ix_persona_translations_language', table_name='persona_translations')
    op.drop_index('ix_persona_translations_persona_id', table_name='persona_translations')
    op.drop_table('persona_translations')


