"""Add start_codes table for acquisition tracking and onboarding

Revision ID: 021
Revises: 020
Create Date: 2025-11-12

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
    """Create start_codes table"""
    # Check if table already exists to make migration idempotent
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    
    if 'start_codes' not in tables:
        op.create_table(
            'start_codes',
            sa.Column('code', sa.String(length=5), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('persona_id', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('history_id', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['persona_id'], ['personas.id'], ),
            sa.ForeignKeyConstraint(['history_id'], ['persona_history_starts.id'], ),
            sa.PrimaryKeyConstraint('code')
        )
        
        # Create indexes
        op.create_index('ix_start_codes_is_active', 'start_codes', ['is_active'])


def downgrade():
    """Drop start_codes table"""
    # Check if table exists before trying to drop it
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    
    if 'start_codes' in tables:
        op.drop_index('ix_start_codes_is_active', table_name='start_codes')
        op.drop_table('start_codes')

