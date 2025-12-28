"""Add ad_price field to start_codes table

Revision ID: 028
Revises: 027
Create Date: 2025-12-29
"""
from alembic import op
import sqlalchemy as sa


revision = '028'
down_revision = 'add_text_ru_col'
branch_labels = None
depends_on = None


def upgrade():
    """Add ad_price column to start_codes table"""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    if 'start_codes' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('start_codes')]
        if 'ad_price' not in columns:
            op.add_column('start_codes', 
                sa.Column('ad_price', sa.Numeric(precision=10, scale=4), nullable=True, 
                         comment='Advertisement price in USD for ROI calculations')
            )


def downgrade():
    """Remove ad_price column from start_codes table"""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    if 'start_codes' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('start_codes')]
        if 'ad_price' in columns:
            op.drop_column('start_codes', 'ad_price')

