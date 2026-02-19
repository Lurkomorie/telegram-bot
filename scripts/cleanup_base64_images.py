"""
Cleanup script to migrate base64 images from database to Cloudflare.

This script:
1. Finds all ImageJob records with blurred_original_data (base64) in ext
2. Uploads each image to Cloudflare
3. Replaces blurred_original_data with blurred_original_url
4. Saves the change to database

This will significantly reduce Postgres volume usage.

Run with: python scripts/cleanup_base64_images.py [--dry-run] [--limit N]
"""
import asyncio
import argparse
import base64
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.base import get_db
from app.db.models import ImageJob
from app.core.cloudflare_upload import upload_to_cloudflare_tg
from sqlalchemy.orm.attributes import flag_modified


async def cleanup_base64_images(dry_run: bool = False, limit: int = None):
    """Migrate base64 images to Cloudflare URLs"""
    
    print("=" * 60)
    print("Base64 Image Cleanup Script")
    print("=" * 60)
    print(f"Mode: {'DRY RUN (no changes)' if dry_run else 'LIVE (will modify database)'}")
    if limit:
        print(f"Limit: {limit} records")
    print()
    
    with get_db() as db:
        # Find all jobs with blurred_original_data
        query = db.query(ImageJob).filter(
            ImageJob.ext.isnot(None)
        )
        
        # We need to check JSON field, can't do this efficiently in SQL
        # So we'll iterate and filter in Python
        all_jobs = query.all()
        
        jobs_with_base64 = []
        total_size_bytes = 0
        
        for job in all_jobs:
            if job.ext and 'blurred_original_data' in job.ext:
                base64_data = job.ext.get('blurred_original_data', '')
                size = len(base64_data)
                total_size_bytes += size
                jobs_with_base64.append((job, size))
        
        print(f"Found {len(jobs_with_base64)} jobs with base64 images")
        print(f"Total base64 data size: {total_size_bytes / 1024 / 1024:.2f} MB")
        print()
        
        if not jobs_with_base64:
            print("No base64 images to clean up!")
            return
        
        if limit:
            jobs_with_base64 = jobs_with_base64[:limit]
            print(f"Processing first {limit} jobs")
        
        success_count = 0
        error_count = 0
        saved_bytes = 0
        
        for i, (job, size) in enumerate(jobs_with_base64, 1):
            print(f"\n[{i}/{len(jobs_with_base64)}] Processing job {job.id}...")
            print(f"  Base64 size: {size / 1024:.1f} KB")
            
            if dry_run:
                print("  [DRY RUN] Would upload to Cloudflare and update database")
                success_count += 1
                saved_bytes += size
                continue
            
            try:
                # Decode base64 to binary
                image_data = base64.b64decode(job.ext['blurred_original_data'])
                print(f"  Decoded image: {len(image_data)} bytes")
                
                # Upload to Cloudflare
                filename = f"migrated_blurred_{job.id}.png"
                result = await upload_to_cloudflare_tg(image_data, filename)
                
                if result.success:
                    print(f"  ✅ Uploaded to Cloudflare: {result.image_url[:60]}...")
                    
                    # Update job.ext: remove base64, add URL
                    del job.ext['blurred_original_data']
                    job.ext['blurred_original_url'] = result.image_url
                    flag_modified(job, "ext")
                    db.commit()
                    
                    print(f"  ✅ Database updated")
                    success_count += 1
                    saved_bytes += size
                else:
                    print(f"  ❌ Cloudflare upload failed: {result.error}")
                    error_count += 1
                    
            except Exception as e:
                print(f"  ❌ Error: {e}")
                error_count += 1
                db.rollback()
        
        print()
        print("=" * 60)
        print("Summary")
        print("=" * 60)
        print(f"Processed: {len(jobs_with_base64)} jobs")
        print(f"Success: {success_count}")
        print(f"Errors: {error_count}")
        print(f"Database space saved: {saved_bytes / 1024 / 1024:.2f} MB")
        
        if dry_run:
            print()
            print("This was a DRY RUN. Run without --dry-run to apply changes.")


def main():
    parser = argparse.ArgumentParser(description='Migrate base64 images to Cloudflare')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    parser.add_argument('--limit', type=int, help='Limit number of records to process')
    args = parser.parse_args()
    
    asyncio.run(cleanup_base64_images(dry_run=args.dry_run, limit=args.limit))


if __name__ == "__main__":
    main()
