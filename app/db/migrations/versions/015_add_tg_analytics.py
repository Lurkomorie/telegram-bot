"""Add analytics events table

Revision ID: 015
Revises: 014
Create Date: 2025-10-27

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, BIGINT

# revision identifiers, used by Alembic.
revision = '015'
down_revision = '014'
branch_labels = None
depends_on = None


def upgrade():
    """Create analytics events table"""
    op.create_table(
        'tg_analytics_events',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('client_id', BIGINT, nullable=False),
        sa.Column('event_name', sa.String(100), nullable=False),
        sa.Column('persona_id', UUID(as_uuid=True), nullable=True),
        sa.Column('persona_name', sa.String(255), nullable=True),
        sa.Column('message', sa.Text, nullable=True),
        sa.Column('prompt', sa.Text, nullable=True),
        sa.Column('negative_prompt', sa.Text, nullable=True),
        sa.Column('image_url', sa.Text, nullable=True),
        sa.Column('meta', JSONB, default={}, nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    )
    
    # Create indexes for efficient querying
    op.create_index('ix_tg_analytics_client_id', 'tg_analytics_events', ['client_id'])
    op.create_index('ix_tg_analytics_event_name', 'tg_analytics_events', ['event_name'])
    op.create_index('ix_tg_analytics_created_at', 'tg_analytics_events', ['created_at'])
    op.create_index('ix_tg_analytics_client_created', 'tg_analytics_events', ['client_id', 'created_at'])


def downgrade():
    """Drop analytics events table"""
    op.drop_index('ix_tg_analytics_client_created', 'tg_analytics_events')
    op.drop_index('ix_tg_analytics_created_at', 'tg_analytics_events')
    op.drop_index('ix_tg_analytics_event_name', 'tg_analytics_events')
    op.drop_index('ix_tg_analytics_client_id', 'tg_analytics_events')
    op.drop_table('tg_analytics_events')









