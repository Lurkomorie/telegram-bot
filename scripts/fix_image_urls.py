"""
Fix ImageJob.result_url by copying Cloudflare URLs from TgAnalyticsEvent.

The analytics events have the real Cloudflare URLs (stored in image_url field),
while ImageJob.result_url has placeholder "binary:XXXXXXX".

This script copies the Cloudflare URLs from analytics events to ImageJob.

Run with: python scripts/fix_image_urls.py
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.base import get_db
from app.db.models import TgAnalyticsEvent, ImageJob
from app.db.crud import compute_prompt_hash

BATCH_SIZE = 5000


def fix_image_urls():
    """Copy Cloudflare URLs from analytics events to ImageJob.result_url using bulk UPDATE"""
    print("\n" + "="*60)
    print("FIX IMAGE URLS (Bulk Batch)")
    print("="*60)
    print(f"Batch size: {BATCH_SIZE}")
    print(f"Delay between batches: 2 seconds")
    
    from sqlalchemy import text
    import time
    
    total_updated = 0
    batch_num = 0
    
    while True:
        batch_num += 1
        
        with get_db() as db:
            # Single bulk UPDATE for batch - much faster than individual updates
            # Uses a subquery to get job_id -> cf_url mapping, then updates in one go
            result = db.execute(text("""
                UPDATE image_jobs 
                SET result_url = subq.cf_url
                FROM (
                    SELECT DISTINCT ON ((e.meta->>'job_id')::uuid) 
                        (e.meta->>'job_id')::uuid as job_id,
                        e.image_url as cf_url
                    FROM tg_analytics_events e
                    JOIN image_jobs j ON j.id = (e.meta->>'job_id')::uuid
                    WHERE e.event_name = 'image_generated'
                    AND e.image_url LIKE 'https://imagedelivery.net/%'
                    AND e.meta->>'job_id' IS NOT NULL
                    AND (j.result_url IS NULL 
                         OR j.result_url LIKE 'binary:%'
                         OR j.result_url = '')
                    LIMIT :batch_size
                ) subq
                WHERE image_jobs.id = subq.job_id
            """), {"batch_size": BATCH_SIZE})
            
            updated_count = result.rowcount
            db.commit()
            
            if updated_count == 0:
                print(f"\n✅ Done! Total updated: {total_updated}")
                break
            
            total_updated += updated_count
            print(f"📦 Batch {batch_num}: Updated {updated_count}, Total: {total_updated}")
            
            # 2 second delay between batches
            print(f"   ⏳ Waiting 2 seconds...")
            time.sleep(2)
    
    return total_updated


def get_stats():
    """Get current stats"""
    with get_db() as db:
        total = db.query(ImageJob).count()
        with_cloudflare = db.query(ImageJob).filter(
            ImageJob.result_url.like('https://imagedelivery.net/%')
        ).count()
        with_binary = db.query(ImageJob).filter(
            ImageJob.result_url.like('binary:%')
        ).count()
        with_hash = db.query(ImageJob).filter(
            ImageJob.prompt_hash.isnot(None)
        ).count()
        
        return {
            "total": total,
            "with_cloudflare": with_cloudflare,
            "with_binary": with_binary,
            "with_hash": with_hash
        }


def main():
    print("\n" + "="*60)
    print("IMAGE URL FIX MIGRATION")
    print("="*60)
    
    # Get initial stats
    print("\n📊 Initial stats:")
    stats = get_stats()
    print(f"   Total images: {stats['total']}")
    print(f"   With Cloudflare URL: {stats['with_cloudflare']}")
    print(f"   With binary placeholder: {stats['with_binary']}")
    print(f"   With prompt_hash: {stats['with_hash']}")
    
    # Run migration
    updated = fix_image_urls()
    
    # Final stats
    print("\n" + "="*60)
    print("MIGRATION COMPLETE")
    print("="*60)
    final_stats = get_stats()
    print(f"\n📊 Final stats:")
    print(f"   Total images: {final_stats['total']}")
    print(f"   With Cloudflare URL: {final_stats['with_cloudflare']}")
    print(f"   With binary placeholder: {final_stats['with_binary']}")
    print(f"   With prompt_hash: {final_stats['with_hash']}")
    print(f"\n📈 Updated: {updated} ImageJobs")


if __name__ == "__main__":
    main()
