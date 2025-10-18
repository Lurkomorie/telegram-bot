"""Multi-brain pipeline schema updates

Revision ID: 002
Revises: 001
Create Date: 2025-01-16 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ========== PERSONAS TABLE UPDATES ==========
    
    # Add new columns to personas
    op.add_column('personas', sa.Column('prompt', sa.Text(), nullable=True))
    op.add_column('personas', sa.Column('badges', postgresql.ARRAY(sa.String()), server_default='{}', nullable=False))
    op.add_column('personas', sa.Column('visibility', sa.String(length=20), server_default='custom', nullable=False))
    op.add_column('personas', sa.Column('description', sa.Text(), nullable=True))
    op.add_column('personas', sa.Column('intro', sa.Text(), nullable=True))
    
    # Add check constraint for visibility
    op.create_check_constraint(
        'personas_visibility_check',
        'personas',
        "visibility IN ('public', 'private', 'custom')"
    )
    
    # Create index on visibility
    op.create_index('ix_personas_visibility', 'personas', ['visibility'], unique=False)
    
    # Migrate data: is_preset -> visibility
    op.execute("""
        UPDATE personas 
        SET visibility = CASE 
            WHEN is_preset = true THEN 'public'
            ELSE 'custom'
        END
    """)
    
    # Drop old columns (will cascade old constraints)
    op.drop_column('personas', 'system_prompt')
    op.drop_column('personas', 'is_preset')
    op.drop_column('personas', 'appearance')
    op.drop_column('personas', 'style')
    op.drop_column('personas', 'negatives')
    
    # ========== CREATE PERSONA_HISTORY_STARTS TABLE ==========
    op.create_table(
        'persona_history_starts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('persona_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('image_url', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['persona_id'], ['personas.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_persona_history_starts_persona_id', 'persona_history_starts', ['persona_id'], unique=False)
    
    # ========== MESSAGES TABLE UPDATES ==========
    op.add_column('messages', sa.Column('is_processed', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('messages', sa.Column('state_snapshot', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    
    # Create index for unprocessed messages query
    op.create_index('ix_messages_unprocessed', 'messages', ['chat_id', 'is_processed'], unique=False)
    
    # ========== CHATS TABLE UPDATES ==========
    op.add_column('chats', sa.Column('last_user_message_at', sa.DateTime(), nullable=True))
    op.add_column('chats', sa.Column('last_assistant_message_at', sa.DateTime(), nullable=True))
    
    # Create index for auto-message queries
    op.create_index('ix_chats_last_user_message_at', 'chats', ['last_user_message_at'], unique=False)


def downgrade() -> None:
    # ========== CHATS TABLE DOWNGRADE ==========
    op.drop_index('ix_chats_last_user_message_at', table_name='chats')
    op.drop_column('chats', 'last_assistant_message_at')
    op.drop_column('chats', 'last_user_message_at')
    
    # ========== MESSAGES TABLE DOWNGRADE ==========
    op.drop_index('ix_messages_unprocessed', table_name='messages')
    op.drop_column('messages', 'state_snapshot')
    op.drop_column('messages', 'is_processed')
    
    # ========== PERSONA_HISTORY_STARTS TABLE DOWNGRADE ==========
    op.drop_index('ix_persona_history_starts_persona_id', table_name='persona_history_starts')
    op.drop_table('persona_history_starts')
    
    # ========== PERSONAS TABLE DOWNGRADE ==========
    # Re-add old columns
    op.add_column('personas', sa.Column('negatives', sa.Text(), nullable=True))
    op.add_column('personas', sa.Column('style', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('personas', sa.Column('appearance', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('personas', sa.Column('is_preset', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('personas', sa.Column('system_prompt', sa.Text(), nullable=False))
    
    # Drop new columns
    op.drop_index('ix_personas_visibility', table_name='personas')
    op.drop_constraint('personas_visibility_check', 'personas', type_='check')
    op.drop_column('personas', 'intro')
    op.drop_column('personas', 'description')
    op.drop_column('personas', 'visibility')
    op.drop_column('personas', 'badges')
    op.drop_column('personas', 'prompt')


