"""Add image cache fields

Add fields for image caching system:
- prompt_hash: SHA256 hash of normalized prompt for fast lookup
- refresh_count: How many times users refreshed this image
- cache_serve_count: How many times served from cache
- is_blacklisted: Bad image - don't serve from cache

Also create user_shown_images table for tracking which images users have seen.

Revision ID: 030_image_cache
Revises: 
Create Date: 2026-01-23
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers
revision = '030_image_cache'
down_revision = '832ab5755258'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns to image_jobs table
    op.add_column('image_jobs', sa.Column('prompt_hash', sa.String(64), nullable=True))
    op.add_column('image_jobs', sa.Column('refresh_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('image_jobs', sa.Column('cache_serve_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('image_jobs', sa.Column('is_blacklisted', sa.Boolean(), nullable=False, server_default='false'))
    
    # Create index for fast cache lookup
    op.create_index('ix_image_jobs_prompt_hash', 'image_jobs', ['prompt_hash'])
    
    # Create user_shown_images table
    op.create_table(
        'user_shown_images',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', sa.BigInteger(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('image_job_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('image_jobs.id'), nullable=False),
        sa.Column('shown_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    
    # Create unique index for user_shown_images
    op.create_index(
        'ix_user_shown_images_lookup',
        'user_shown_images',
        ['user_id', 'image_job_id'],
        unique=True
    )


def downgrade() -> None:
    # Drop user_shown_images table
    op.drop_index('ix_user_shown_images_lookup', table_name='user_shown_images')
    op.drop_table('user_shown_images')
    
    # Drop index and columns from image_jobs
    op.drop_index('ix_image_jobs_prompt_hash', table_name='image_jobs')
    op.drop_column('image_jobs', 'is_blacklisted')
    op.drop_column('image_jobs', 'cache_serve_count')
    op.drop_column('image_jobs', 'refresh_count')
    op.drop_column('image_jobs', 'prompt_hash')
