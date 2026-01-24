"""
Fast DB cleanup - delete old images from database only (no Cloudflare).
Saves Cloudflare image IDs to file for later deletion.

Run with: python scripts/cleanup_db_fast.py
"""
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import or_, text
from app.db.base import get_db
from app.db.models import ImageJob, UserShownImage
from app.db.crud import compute_prompt_hash
from app.core.cloudflare_upload import extract_image_id_from_url

# Configuration
CUTOFF_DATE = datetime(2026, 1, 13)
BATCH_SIZE = 5000
CF_IDS_FILE = "/tmp/cloudflare_ids_to_delete.txt"


def cleanup_db_fast():
    """Fast delete from DB, save Cloudflare IDs for later"""
    import time
    
    print("\n" + "="*60)
    print("FAST DB CLEANUP")
    print("="*60)
    print(f"Cutoff date: {CUTOFF_DATE}")
    print(f"Batch size: {BATCH_SIZE}")
    
    total_deleted = 0
    cf_ids = []
    batch_num = 0
    
    while True:
        batch_num += 1
        
        with get_db() as db:
            # Find images to delete
            jobs = db.query(ImageJob).filter(
                or_(
                    ImageJob.created_at < CUTOFF_DATE,
                    ~ImageJob.result_url.like("https://imagedelivery.net/%"),
                    ImageJob.result_url.is_(None)
                )
            ).limit(BATCH_SIZE).all()
            
            if not jobs:
                print(f"\n✅ DB cleanup done! Deleted: {total_deleted}")
                break
            
            print(f"📦 Batch {batch_num}: Deleting {len(jobs)} from DB...")
            
            # Collect job IDs and Cloudflare IDs
            job_ids = []
            for job in jobs:
                job_ids.append(job.id)
                if job.result_url and "imagedelivery.net" in job.result_url:
                    cf_id = extract_image_id_from_url(job.result_url)
                    if cf_id:
                        cf_ids.append(cf_id)
            
            # First delete from user_shown_images (foreign key constraint)
            db.query(UserShownImage).filter(UserShownImage.image_job_id.in_(job_ids)).delete(synchronize_session=False)
            
            # Then delete the jobs
            db.query(ImageJob).filter(ImageJob.id.in_(job_ids)).delete(synchronize_session=False)
            
            db.commit()
            total_deleted += len(jobs)
            print(f"   ✅ Deleted {len(jobs)}, Total: {total_deleted}, CF IDs collected: {len(cf_ids)}")
            
            time.sleep(0.5)
    
    # Save Cloudflare IDs to file
    if cf_ids:
        with open(CF_IDS_FILE, 'w') as f:
            f.write('\n'.join(cf_ids))
        print(f"\n💾 Saved {len(cf_ids)} Cloudflare IDs to {CF_IDS_FILE}")
        print(f"   Run 'python scripts/cleanup_cloudflare.py' to delete from Cloudflare")
    
    return total_deleted, len(cf_ids)


def fill_hashes():
    """Fill prompt_hash for remaining images"""
    import time
    
    print("\n" + "="*60)
    print("FILL PROMPT HASHES")
    print("="*60)
    
    total = 0
    batch_num = 0
    
    while True:
        batch_num += 1
        
        with get_db() as db:
            jobs = db.query(ImageJob).filter(
                ImageJob.prompt_hash.is_(None),
                ImageJob.prompt.isnot(None)
            ).limit(BATCH_SIZE).all()
            
            if not jobs:
                print(f"\n✅ Hash filling done! Updated: {total}")
                break
            
            print(f"📦 Batch {batch_num}: Updating {len(jobs)} hashes...")
            
            for job in jobs:
                job.prompt_hash = compute_prompt_hash(job.prompt)
            
            db.commit()
            total += len(jobs)
            print(f"   ✅ Updated {len(jobs)}, Total: {total}")
            
            time.sleep(0.5)
    
    return total


def main():
    print("\n" + "="*60)
    print("FAST CLEANUP + HASH FILL")
    print("="*60)
    
    # Phase 1: Fast DB delete
    deleted, cf_count = cleanup_db_fast()
    
    # Phase 2: Fill hashes
    hashes = fill_hashes()
    
    # Final stats
    with get_db() as db:
        total = db.query(ImageJob).count()
        with_cf = db.query(ImageJob).filter(
            ImageJob.result_url.like("https://imagedelivery.net/%")
        ).count()
        with_hash = db.query(ImageJob).filter(
            ImageJob.prompt_hash.isnot(None)
        ).count()
    
    print("\n" + "="*60)
    print("DONE!")
    print("="*60)
    print(f"Deleted from DB: {deleted}")
    print(f"Cloudflare IDs saved: {cf_count}")
    print(f"Hashes filled: {hashes}")
    print(f"\nFinal stats:")
    print(f"   Total images: {total}")
    print(f"   With Cloudflare URL: {with_cf}")
    print(f"   With prompt_hash: {with_hash}")
    
    if cf_count > 0:
        print(f"\n⚠️  Run 'python scripts/cleanup_cloudflare.py' to delete from Cloudflare!")


if __name__ == "__main__":
    main()
