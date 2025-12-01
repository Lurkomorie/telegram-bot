"""Add system messages tables

Revision ID: 021
Revises: 020
Create Date: 2025-01-15

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '021'
down_revision = '020'
branch_labels = None
depends_on = None


def upgrade():
    """Add system message tables"""
    # Create system_message_templates table
    op.create_table(
        'system_message_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('title', sa.String(255), nullable=True),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('media_type', sa.String(20), nullable=False, server_default='none'),
        sa.Column('media_url', sa.Text(), nullable=True),
        sa.Column('buttons', postgresql.JSONB(), nullable=True),
        sa.Column('created_by', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint("media_type IN ('none', 'photo', 'video', 'animation')", name='system_message_templates_media_type_check')
    )
    op.create_index('ix_system_message_templates_is_active', 'system_message_templates', ['is_active'])
    op.create_index('ix_system_message_templates_created_at', 'system_message_templates', ['created_at'])
    
    # Create system_messages table
    op.create_table(
        'system_messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('title', sa.String(255), nullable=True),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('media_type', sa.String(20), nullable=False, server_default='none'),
        sa.Column('media_url', sa.Text(), nullable=True),
        sa.Column('buttons', postgresql.JSONB(), nullable=True),
        sa.Column('target_type', sa.String(20), nullable=False),
        sa.Column('target_user_ids', postgresql.ARRAY(sa.BigInteger()), nullable=True),
        sa.Column('target_group', sa.String(255), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='draft'),
        sa.Column('send_immediately', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('scheduled_at', sa.DateTime(), nullable=True),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.String(255), nullable=True),
        sa.Column('ext', postgresql.JSONB(), nullable=True),
        sa.Column('template_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint("media_type IN ('none', 'photo', 'video', 'animation')", name='system_messages_media_type_check'),
        sa.CheckConstraint("target_type IN ('all', 'user', 'users', 'group')", name='system_messages_target_type_check'),
        sa.CheckConstraint("status IN ('draft', 'scheduled', 'sending', 'completed', 'failed', 'cancelled')", name='system_messages_status_check'),
        sa.ForeignKeyConstraint(['template_id'], ['system_message_templates.id'], name='system_messages_template_id_fkey')
    )
    op.create_index('ix_system_messages_status', 'system_messages', ['status'])
    op.create_index('ix_system_messages_target_type', 'system_messages', ['target_type'])
    op.create_index('ix_system_messages_scheduled_at', 'system_messages', ['scheduled_at'])
    op.create_index('ix_system_messages_created_at', 'system_messages', ['created_at'])
    op.create_index('ix_system_messages_template_id', 'system_messages', ['template_id'])
    
    # Create system_message_deliveries table
    op.create_table(
        'system_message_deliveries',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('system_message_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('max_retries', sa.BigInteger(), nullable=False, server_default='3'),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('message_id', sa.BigInteger(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint("status IN ('pending', 'sent', 'failed', 'blocked')", name='system_message_deliveries_status_check'),
        sa.ForeignKeyConstraint(['system_message_id'], ['system_messages.id'], ondelete='CASCADE', name='system_message_deliveries_system_message_id_fkey'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='system_message_deliveries_user_id_fkey')
    )
    op.create_index('ix_system_message_deliveries_system_message_id', 'system_message_deliveries', ['system_message_id'])
    op.create_index('ix_system_message_deliveries_user_id', 'system_message_deliveries', ['user_id'])
    op.create_index('ix_system_message_deliveries_status', 'system_message_deliveries', ['status'])
    op.create_index('ix_system_message_deliveries_retry_count', 'system_message_deliveries', ['retry_count'])


def downgrade():
    """Remove system message tables"""
    op.drop_table('system_message_deliveries')
    op.drop_table('system_messages')
    op.drop_table('system_message_templates')

