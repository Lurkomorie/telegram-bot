"""Update image cache lookup index for file_id-first cache policy

Revision ID: 035_cache_lookup_fileid
Revises: 034_chat_purchase_nullable_chat
Create Date: 2026-02-23
"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "035_cache_lookup_fileid"
down_revision = "034_chat_purchase_nullable_chat"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_image_jobs_cache_lookup")
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_image_jobs_cache_lookup
        ON image_jobs (prompt_hash, cache_serve_count DESC, created_at DESC)
        WHERE status = 'completed'
          AND is_blacklisted = FALSE
          AND (
            result_file_id IS NOT NULL
            OR (result_url IS NOT NULL AND result_url NOT LIKE 'binary:%')
          )
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_image_jobs_cache_lookup")
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_image_jobs_cache_lookup
        ON image_jobs (prompt_hash)
        WHERE status = 'completed'
          AND is_blacklisted = FALSE
          AND result_url LIKE 'https://imagedelivery.net/%'
        """
    )
