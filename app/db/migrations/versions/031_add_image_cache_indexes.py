"""Add optimized indexes for image cache system

Revision ID: 031_add_image_cache_indexes
Revises: 030_add_image_cache_fields
Create Date: 2026-01-24

These indexes optimize the image cache lookup queries:
1. ix_image_jobs_cache_lookup - Partial index for find_cached_image() - the main cache query
2. ix_image_jobs_refresh_count - For /most-refreshed-images analytics endpoint
3. ix_image_jobs_cache_serve_count - For /most-cached-images analytics endpoint  
4. ix_user_shown_images_user_id - For NOT IN subquery in cache lookup
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '031_add_image_cache_indexes'
down_revision = '030_add_image_cache_fields'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Partial index for cache lookup - most important for performance
    # This index only includes rows that are valid cache candidates
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_image_jobs_cache_lookup 
        ON image_jobs (prompt_hash) 
        WHERE status = 'completed' 
          AND is_blacklisted = FALSE 
          AND result_url LIKE 'https://imagedelivery.net/%'
    """)
    
    # 2. Partial index for refresh_count analytics
    # Only index rows with refresh_count > 0 (images that were actually refreshed)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_image_jobs_refresh_count 
        ON image_jobs (refresh_count DESC) 
        WHERE refresh_count > 0
    """)
    
    # 3. Partial index for cache_serve_count analytics
    # Only index rows with cache_serve_count > 0 (images that were served from cache)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_image_jobs_cache_serve_count 
        ON image_jobs (cache_serve_count DESC) 
        WHERE cache_serve_count > 0
    """)
    
    # 4. Index on user_shown_images.user_id for faster NOT IN subquery
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_user_shown_images_user_id 
        ON user_shown_images (user_id)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_image_jobs_cache_lookup")
    op.execute("DROP INDEX IF EXISTS ix_image_jobs_refresh_count")
    op.execute("DROP INDEX IF EXISTS ix_image_jobs_cache_serve_count")
    op.execute("DROP INDEX IF EXISTS ix_user_shown_images_user_id")
