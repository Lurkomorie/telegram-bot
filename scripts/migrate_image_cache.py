"""
Migration script for image cache system.

This script:
1. Deletes images older than January 13, 2026 from DB AND Cloudflare CDN
2. Deletes images without Cloudflare URL from DB
3. Fills prompt_hash for remaining images

Run with: python scripts/migrate_image_cache.py
"""
import sys
import asyncio
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import or_
from app.db.base import get_db
from app.db.models import ImageJob
from app.db.crud import compute_prompt_hash
from app.core.cloudflare_upload import extract_image_id_from_url, delete_from_cloudflare

# Configuration
CUTOFF_DATE = datetime(2026, 1, 13)  # Delete everything before this date
BATCH_SIZE_DELETE = 500  # Batches for deletion (includes Cloudflare API calls)
BATCH_SIZE_HASH = 5000  # Larger batches for hash filling (no API calls)
DELAY_BETWEEN_BATCHES = 0.5  # seconds


async def cleanup_old_images():
    """Phase 1: Delete images before Jan 13 + images without Cloudflare URL"""
    print("\n" + "="*60)
    print("PHASE 1: Cleanup old/invalid images")
    print("="*60)
    print(f"Cutoff date: {CUTOFF_DATE}")
    print(f"Batch size: {BATCH_SIZE_DELETE}")
    print(f"Delay between batches: {DELAY_BETWEEN_BATCHES}s")
    
    total_deleted = 0
    total_cf_deleted = 0
    batch_num = 0
    
    while True:
        batch_num += 1
        
        with get_db() as db:
            # Find images to delete:
            # 1. Created before cutoff date, OR
            # 2. Don't have cloudflare URL (result_url not starting with imagedelivery.net)
            jobs_to_delete = db.query(ImageJob).filter(
                or_(
                    ImageJob.created_at < CUTOFF_DATE,
                    ~ImageJob.result_url.like("https://imagedelivery.net/%"),
                    ImageJob.result_url.is_(None)
                )
            ).limit(BATCH_SIZE_DELETE).all()
            
            if not jobs_to_delete:
                print(f"\n✅ Cleanup complete! Total deleted: {total_deleted} images ({total_cf_deleted} from Cloudflare)")
                break
            
            print(f"\n📦 Batch {batch_num}: Processing {len(jobs_to_delete)} images...")
            
            cf_deleted_in_batch = 0
            for job in jobs_to_delete:
                # Try to delete from Cloudflare if it has a cloudflare URL
                if job.result_url and "imagedelivery.net" in job.result_url:
                    cf_image_id = extract_image_id_from_url(job.result_url)
                    if cf_image_id:
                        success = await delete_from_cloudflare(cf_image_id)
                        if success:
                            cf_deleted_in_batch += 1
                            total_cf_deleted += 1
                
                # Delete from database
                db.delete(job)
            
            db.commit()
            total_deleted += len(jobs_to_delete)
            
            print(f"   ✅ Deleted {len(jobs_to_delete)} from DB ({cf_deleted_in_batch} from Cloudflare)")
            print(f"   📊 Total so far: {total_deleted} deleted")
        
        # Delay between batches to not overwhelm the DB/API
        await asyncio.sleep(DELAY_BETWEEN_BATCHES)
    
    return total_deleted, total_cf_deleted


def fill_prompt_hashes():
    """Phase 2: Fill prompt_hash for remaining images without hash"""
    print("\n" + "="*60)
    print("PHASE 2: Fill prompt_hash for remaining images")
    print("="*60)
    print(f"Batch size: {BATCH_SIZE_HASH}")
    
    total_updated = 0
    batch_num = 0
    
    while True:
        batch_num += 1
        
        with get_db() as db:
            # Find images without prompt_hash
            jobs = db.query(ImageJob).filter(
                ImageJob.prompt_hash.is_(None),
                ImageJob.prompt.isnot(None)
            ).limit(BATCH_SIZE_HASH).all()
            
            if not jobs:
                print(f"\n✅ Hash filling complete! Total updated: {total_updated} images")
                break
            
            print(f"\n📦 Batch {batch_num}: Processing {len(jobs)} images...")
            
            for job in jobs:
                job.prompt_hash = compute_prompt_hash(job.prompt)
            
            db.commit()
            total_updated += len(jobs)
            
            print(f"   ✅ Updated {len(jobs)} images with prompt_hash")
            print(f"   📊 Total so far: {total_updated} updated")
    
    return total_updated


def get_stats():
    """Get current stats before migration"""
    with get_db() as db:
        total = db.query(ImageJob).count()
        before_cutoff = db.query(ImageJob).filter(ImageJob.created_at < CUTOFF_DATE).count()
        without_cf = db.query(ImageJob).filter(
            or_(
                ~ImageJob.result_url.like("https://imagedelivery.net/%"),
                ImageJob.result_url.is_(None)
            )
        ).count()
        with_hash = db.query(ImageJob).filter(ImageJob.prompt_hash.isnot(None)).count()
        
        return {
            "total": total,
            "before_cutoff": before_cutoff,
            "without_cf": without_cf,
            "with_hash": with_hash
        }


async def main():
    """Main migration function"""
    print("\n" + "="*60)
    print("IMAGE CACHE MIGRATION")
    print("="*60)
    
    # Get initial stats
    print("\n📊 Initial stats:")
    stats = get_stats()
    print(f"   Total images: {stats['total']}")
    print(f"   Before {CUTOFF_DATE.date()}: {stats['before_cutoff']}")
    print(f"   Without Cloudflare URL: {stats['without_cf']}")
    print(f"   With prompt_hash: {stats['with_hash']}")
    
    # Confirm before proceeding
    print("\n⚠️  This will DELETE images from both database AND Cloudflare CDN!")
    confirm = input("Type 'yes' to proceed: ")
    if confirm.lower() != 'yes':
        print("❌ Aborted")
        return
    
    # Phase 1: Cleanup
    deleted, cf_deleted = await cleanup_old_images()
    
    # Phase 2: Fill hashes
    updated = fill_prompt_hashes()
    
    # Final stats
    print("\n" + "="*60)
    print("MIGRATION COMPLETE")
    print("="*60)
    final_stats = get_stats()
    print(f"\n📊 Final stats:")
    print(f"   Total images: {final_stats['total']}")
    print(f"   With prompt_hash: {final_stats['with_hash']}")
    print(f"\n📈 Summary:")
    print(f"   Deleted from DB: {deleted}")
    print(f"   Deleted from Cloudflare: {cf_deleted}")
    print(f"   Hash filled: {updated}")


if __name__ == "__main__":
    asyncio.run(main())
