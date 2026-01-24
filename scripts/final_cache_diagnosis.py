"""
Final diagnosis - check everything about the cache system
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timedelta
from sqlalchemy import func
from app.db.base import get_db
from app.db.models import ImageJob, UserShownImage


def final_diagnosis():
    """Complete cache system diagnosis"""
    
    five_hours_ago = datetime.utcnow() - timedelta(hours=5)
    
    with get_db() as session:
        print("="*60)
        print("COMPLETE CACHE SYSTEM DIAGNOSIS")
        print("="*60)
        
        # 1. Check user_shown_images table
        print("\n1. USER_SHOWN_IMAGES TABLE")
        print("-"*60)
        total_shown = session.query(UserShownImage).count()
        print(f"Total records: {total_shown}")
        
        if total_shown == 0:
            print("❌ CRITICAL: Table is EMPTY!")
            print("   This means NO images have ever been marked as shown.")
            print("   The cache system cannot work without this tracking.")
        else:
            recent_shown = session.query(UserShownImage).filter(
                UserShownImage.shown_at >= five_hours_ago
            ).count()
            print(f"Recent (last 5h): {recent_shown}")
        
        # 2. Check image job statistics
        print("\n2. IMAGE JOB STATISTICS")
        print("-"*60)
        
        total_jobs = session.query(ImageJob).count()
        completed_jobs = session.query(ImageJob).filter(
            ImageJob.status == 'completed'
        ).count()
        
        print(f"Total image jobs: {total_jobs}")
        print(f"Completed: {completed_jobs}")
        
        # Recent stats
        recent_total = session.query(ImageJob).filter(
            ImageJob.created_at >= five_hours_ago
        ).count()
        recent_completed = session.query(ImageJob).filter(
            ImageJob.created_at >= five_hours_ago,
            ImageJob.status == 'completed'
        ).count()
        
        print(f"\nLast 5 hours:")
        print(f"  Total: {recent_total}")
        print(f"  Completed: {recent_completed}")
        
        # 3. Check cache eligibility
        print("\n3. CACHE ELIGIBILITY")
        print("-"*60)
        
        cache_eligible_all = session.query(ImageJob).filter(
            ImageJob.status == 'completed',
            ImageJob.prompt_hash.isnot(None),
            ImageJob.result_url.like('https://imagedelivery.net/%'),
            ImageJob.is_blacklisted == False
        ).count()
        
        cache_eligible_recent = session.query(ImageJob).filter(
            ImageJob.created_at >= five_hours_ago,
            ImageJob.status == 'completed',
            ImageJob.prompt_hash.isnot(None),
            ImageJob.result_url.like('https://imagedelivery.net/%'),
            ImageJob.is_blacklisted == False
        ).count()
        
        print(f"All time cache-eligible: {cache_eligible_all}")
        print(f"Recent cache-eligible: {cache_eligible_recent}")
        
        if completed_jobs > 0:
            print(f"Eligibility rate: {cache_eligible_all/completed_jobs*100:.1f}%")
        
        # 4. Check cache serve statistics
        print("\n4. CACHE SERVE STATISTICS")
        print("-"*60)
        
        images_served_from_cache = session.query(ImageJob).filter(
            ImageJob.cache_serve_count > 0
        ).count()
        
        total_cache_serves = session.query(
            func.sum(ImageJob.cache_serve_count)
        ).scalar() or 0
        
        print(f"Images ever served from cache: {images_served_from_cache}")
        print(f"Total cache serves: {total_cache_serves}")
        
        recent_cache_serves = session.query(
            func.sum(ImageJob.cache_serve_count)
        ).filter(
            ImageJob.created_at >= five_hours_ago
        ).scalar() or 0
        
        print(f"Recent cache serves: {recent_cache_serves}")
        
        # 5. Check for duplicate prompts
        print("\n5. DUPLICATE PROMPT ANALYSIS")
        print("-"*60)
        
        duplicate_hashes = session.query(
            ImageJob.prompt_hash,
            func.count(ImageJob.id).label('count')
        ).filter(
            ImageJob.prompt_hash.isnot(None),
            ImageJob.status == 'completed'
        ).group_by(ImageJob.prompt_hash).having(
            func.count(ImageJob.id) > 1
        ).count()
        
        print(f"Hashes with multiple images: {duplicate_hashes}")
        
        # Get top duplicates
        top_duplicates = session.query(
            ImageJob.prompt_hash,
            func.count(ImageJob.id).label('count')
        ).filter(
            ImageJob.prompt_hash.isnot(None),
            ImageJob.status == 'completed'
        ).group_by(ImageJob.prompt_hash).having(
            func.count(ImageJob.id) > 1
        ).order_by(func.count(ImageJob.id).desc()).limit(5).all()
        
        if top_duplicates:
            print(f"\nTop 5 most duplicated hashes:")
            for hash_val, count in top_duplicates:
                print(f"  {hash_val[:16]}...: {count} images")
        
        # 6. DIAGNOSIS
        print(f"\n{'='*60}")
        print("DIAGNOSIS")
        print("="*60)
        
        if total_shown == 0:
            print("\n❌ ROOT CAUSE FOUND:")
            print("   The user_shown_images table is EMPTY.")
            print("\n   This means:")
            print("   1. mark_image_shown() is NEVER being called")
            print("   2. Neither for cached images NOR for newly generated images")
            print("\n   WHY THIS BREAKS CACHING:")
            print("   - Cache lookup works (we tested it)")
            print("   - But without tracking, users see same images repeatedly")
            print("   - The system can't deduplicate properly")
            print("\n   FIX:")
            print("   1. Add mark_image_shown() call in /image/callback (DONE)")
            print("   2. Verify it's actually being executed in production")
            print("   3. Check for any exceptions that might be silently failing")
        
        if cache_eligible_all > 0 and total_cache_serves == 0:
            print("\n❌ CACHE NEVER USED:")
            print(f"   {cache_eligible_all} cache-eligible images exist")
            print("   But cache_serve_count is 0 for ALL images")
            print("\n   This means:")
            print("   1. Cache lookup is not being called, OR")
            print("   2. Cache lookup is failing silently, OR")
            print("   3. Prompts are always unique (no duplicates)")
            
            if duplicate_hashes > 0:
                print(f"\n   But we have {duplicate_hashes} duplicate hashes!")
                print("   So prompts ARE being reused.")
                print("\n   CONCLUSION: Cache lookup is not being called or is failing")


if __name__ == "__main__":
    final_diagnosis()
