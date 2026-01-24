"""
Debug why cache lookup is failing for old images
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timedelta
from sqlalchemy import func, exists, and_
from app.db.base import get_db
from app.db.models import ImageJob, UserShownImage


def debug_cache_lookup():
    """Debug cache lookup for a specific hash that should have hits"""
    
    five_hours_ago = datetime.utcnow() - timedelta(hours=5)
    
    with get_db() as session:
        # Find a hash that was used recently AND historically
        recent_with_historical = session.query(
            ImageJob.prompt_hash,
            func.count(ImageJob.id).label('recent_count')
        ).filter(
            ImageJob.created_at >= five_hours_ago,
            ImageJob.prompt_hash.isnot(None),
            ImageJob.status == 'completed'
        ).group_by(ImageJob.prompt_hash).having(
            func.count(ImageJob.id) > 1
        ).order_by(func.count(ImageJob.id).desc()).first()
        
        if not recent_with_historical:
            print("No duplicate hashes found in recent period")
            return
        
        test_hash = recent_with_historical.prompt_hash
        print(f"Testing with hash: {test_hash[:16]}...")
        print(f"Recent uses: {recent_with_historical.recent_count}")
        print("="*60)
        
        # Get all images with this hash
        all_images = session.query(ImageJob).filter(
            ImageJob.prompt_hash == test_hash
        ).order_by(ImageJob.created_at).all()
        
        print(f"\nTotal images with this hash: {len(all_images)}")
        print(f"First created: {all_images[0].created_at}")
        print(f"Last created: {all_images[-1].created_at}")
        
        # Check how many are cache-eligible
        cache_eligible = [img for img in all_images if (
            img.status == 'completed' and
            img.result_url and
            img.result_url.startswith('https://imagedelivery.net/') and
            not img.is_blacklisted
        )]
        
        print(f"\nCache-eligible images: {len(cache_eligible)}")
        
        if len(cache_eligible) == 0:
            print("\n❌ NO CACHE-ELIGIBLE IMAGES!")
            print("\nBreakdown of why images are not eligible:")
            for img in all_images[:10]:
                reasons = []
                if img.status != 'completed':
                    reasons.append(f"status={img.status}")
                if not img.result_url:
                    reasons.append("no URL")
                elif not img.result_url.startswith('https://imagedelivery.net/'):
                    reasons.append(f"wrong URL type: {img.result_url[:50]}")
                if img.is_blacklisted:
                    reasons.append("blacklisted")
                print(f"  - {img.id}: {', '.join(reasons) if reasons else 'ELIGIBLE'}")
            return
        
        # Pick the oldest cache-eligible image
        oldest_eligible = cache_eligible[0]
        print(f"\nOldest cache-eligible image:")
        print(f"  ID: {oldest_eligible.id}")
        print(f"  Created: {oldest_eligible.created_at}")
        print(f"  User: {oldest_eligible.user_id}")
        print(f"  URL: {oldest_eligible.result_url[:80]}...")
        
        # Check UserShownImage table
        print(f"\n{'='*60}")
        print("USER SHOWN IMAGE TRACKING")
        print("="*60)
        
        total_shown_records = session.query(UserShownImage).count()
        print(f"\nTotal records in user_shown_images table: {total_shown_records}")
        
        # Check if ANY images with this hash are marked as shown
        shown_for_hash = session.query(UserShownImage).filter(
            UserShownImage.image_job_id.in_([img.id for img in all_images])
        ).all()
        
        print(f"Images with this hash marked as shown: {len(shown_for_hash)}")
        
        if len(shown_for_hash) == 0:
            print("\n❌ PROBLEM FOUND: No images with this hash are marked as shown!")
            print("This means the cache lookup will ALWAYS find images, even for users who've seen them.")
            print("\nThis explains why cache_serve_count is 0 - the NOT EXISTS check always passes,")
            print("but something else must be preventing cache hits...")
        else:
            print(f"\nShown to users:")
            for shown in shown_for_hash[:5]:
                print(f"  - User {shown.user_id} saw image {shown.image_job_id} at {shown.shown_at}")
        
        # Now simulate cache lookup for a recent user
        print(f"\n{'='*60}")
        print("SIMULATING CACHE LOOKUP")
        print("="*60)
        
        # Get a recent user who requested this hash
        recent_user_img = [img for img in all_images if img.created_at >= five_hours_ago][0]
        test_user_id = recent_user_img.user_id
        
        print(f"\nTest user: {test_user_id}")
        print(f"Recent request at: {recent_user_img.created_at}")
        
        # Simulate the exact cache lookup query
        not_shown = ~exists().where(
            and_(
                UserShownImage.user_id == test_user_id,
                UserShownImage.image_job_id == ImageJob.id
            )
        )
        
        cache_result = session.query(ImageJob).filter(
            ImageJob.prompt_hash == test_hash,
            ImageJob.status == "completed",
            ImageJob.result_url.like("https://imagedelivery.net/%"),
            ImageJob.is_blacklisted == False,
            not_shown
        ).first()
        
        if cache_result:
            print(f"\n✅ Cache lookup WOULD return: {cache_result.id}")
            print(f"   Created: {cache_result.created_at}")
            print(f"   User: {cache_result.user_id}")
            
            # Check if this user has seen this image
            user_seen = session.query(UserShownImage).filter(
                UserShownImage.user_id == test_user_id,
                UserShownImage.image_job_id == cache_result.id
            ).first()
            
            if user_seen:
                print(f"   ⚠️  But user HAS seen this image at {user_seen.shown_at}")
            else:
                print(f"   ✅ User has NOT seen this image - valid cache hit!")
        else:
            print(f"\n❌ Cache lookup returned NOTHING")
            print("\nChecking why...")
            
            # Check each condition
            print("\nImages matching each condition:")
            
            # Just hash
            just_hash = session.query(ImageJob).filter(
                ImageJob.prompt_hash == test_hash
            ).count()
            print(f"  1. Just hash: {just_hash}")
            
            # Hash + status
            hash_status = session.query(ImageJob).filter(
                ImageJob.prompt_hash == test_hash,
                ImageJob.status == "completed"
            ).count()
            print(f"  2. + status=completed: {hash_status}")
            
            # Hash + status + URL
            hash_status_url = session.query(ImageJob).filter(
                ImageJob.prompt_hash == test_hash,
                ImageJob.status == "completed",
                ImageJob.result_url.like("https://imagedelivery.net/%")
            ).count()
            print(f"  3. + Cloudflare URL: {hash_status_url}")
            
            # Hash + status + URL + not blacklisted
            hash_status_url_bl = session.query(ImageJob).filter(
                ImageJob.prompt_hash == test_hash,
                ImageJob.status == "completed",
                ImageJob.result_url.like("https://imagedelivery.net/%"),
                ImageJob.is_blacklisted == False
            ).count()
            print(f"  4. + not blacklisted: {hash_status_url_bl}")
            
            # Hash + status + URL + not blacklisted + not shown
            hash_status_url_bl_shown = session.query(ImageJob).filter(
                ImageJob.prompt_hash == test_hash,
                ImageJob.status == "completed",
                ImageJob.result_url.like("https://imagedelivery.net/%"),
                ImageJob.is_blacklisted == False,
                not_shown
            ).count()
            print(f"  5. + not shown to user: {hash_status_url_bl_shown}")
            
            if hash_status_url_bl_shown > 0:
                print("\n⚠️  Images exist but .first() returned None - this is weird!")
            else:
                print("\n❌ All images have been shown to this user")


if __name__ == "__main__":
    debug_cache_lookup()
