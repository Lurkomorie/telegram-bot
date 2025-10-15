"""Init schema

Revision ID: 001
Revises: 
Create Date: 2025-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('username', sa.String(length=255), nullable=True),
        sa.Column('first_name', sa.String(length=255), nullable=True),
        sa.Column('locale', sa.String(length=10), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('settings', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Create personas table
    op.create_table(
        'personas',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('owner_user_id', sa.BigInteger(), nullable=True),
        sa.Column('key', sa.String(length=100), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('system_prompt', sa.Text(), nullable=False),
        sa.Column('style', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('negatives', sa.Text(), nullable=True),
        sa.Column('appearance', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('is_preset', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['owner_user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key')
    )
    op.create_index('ix_personas_owner_user_id', 'personas', ['owner_user_id'], unique=False)
    op.create_index('ix_personas_key', 'personas', ['key'], unique=False)

    # Create chats table
    op.create_table(
        'chats',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tg_chat_id', sa.BigInteger(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('persona_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('mode', sa.String(length=20), nullable=False),
        sa.Column('settings', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('state_snapshot', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.CheckConstraint("mode IN ('dm', 'group')", name='chats_mode_check'),
        sa.ForeignKeyConstraint(['persona_id'], ['personas.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_chats_tg_chat_id', 'chats', ['tg_chat_id'], unique=False)
    op.create_index('ix_chats_user_persona', 'chats', ['user_id', 'persona_id'], unique=False)

    # Create messages table
    op.create_table(
        'messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('chat_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('text', sa.Text(), nullable=True),
        sa.Column('media', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.CheckConstraint("role IN ('user', 'assistant', 'system')", name='messages_role_check'),
        sa.ForeignKeyConstraint(['chat_id'], ['chats.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_messages_chat_created', 'messages', ['chat_id', 'created_at'], unique=False)

    # Create image_jobs table
    op.create_table(
        'image_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('chat_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('persona_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('prompt', sa.Text(), nullable=False),
        sa.Column('negative_prompt', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('result_url', sa.Text(), nullable=True),
        sa.Column('result_file_id', sa.String(length=255), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('ext', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.CheckConstraint("status IN ('queued', 'running', 'completed', 'failed')", name='image_jobs_status_check'),
        sa.ForeignKeyConstraint(['chat_id'], ['chats.id'], ),
        sa.ForeignKeyConstraint(['persona_id'], ['personas.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_image_jobs_status', 'image_jobs', ['status'], unique=False)
    op.create_index('ix_image_jobs_chat_id', 'image_jobs', ['chat_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_image_jobs_chat_id', table_name='image_jobs')
    op.drop_index('ix_image_jobs_status', table_name='image_jobs')
    op.drop_table('image_jobs')
    
    op.drop_index('ix_messages_chat_created', table_name='messages')
    op.drop_table('messages')
    
    op.drop_index('ix_chats_user_persona', table_name='chats')
    op.drop_index('ix_chats_tg_chat_id', table_name='chats')
    op.drop_table('chats')
    
    op.drop_index('ix_personas_key', table_name='personas')
    op.drop_index('ix_personas_owner_user_id', table_name='personas')
    op.drop_table('personas')
    
    op.drop_table('users')


