"""
Simulate what happens during a real image request
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timedelta
from app.db.base import get_db
from app.db import crud
from app.db.models import ImageJob
from sqlalchemy import func


def simulate_request():
    """Simulate a real image generation request"""
    
    five_hours_ago = datetime.utcnow() - timedelta(hours=5)
    
    with get_db() as session:
        # Find a hash that was used multiple times (should have cache hits)
        popular_hash = session.query(
            ImageJob.prompt_hash,
            func.count(ImageJob.id).label('count')
        ).filter(
            ImageJob.prompt_hash.isnot(None),
            ImageJob.status == 'completed',
            ImageJob.result_url.like('https://imagedelivery.net/%'),
            ImageJob.is_blacklisted == False
        ).group_by(ImageJob.prompt_hash).having(
            func.count(ImageJob.id) > 10
        ).order_by(func.count(ImageJob.id).desc()).first()
        
        if not popular_hash:
            print("No popular hashes found")
            return
        
        test_hash = popular_hash.prompt_hash
        print(f"Testing with popular hash: {test_hash[:16]}...")
        print(f"Total images with this hash: {popular_hash.count}")
        print("="*60)
        
        # Get all images with this hash
        all_images = session.query(ImageJob).filter(
            ImageJob.prompt_hash == test_hash,
            ImageJob.status == 'completed',
            ImageJob.result_url.like('https://imagedelivery.net/%'),
            ImageJob.is_blacklisted == False
        ).order_by(ImageJob.created_at).all()
        
        print(f"\nCache-eligible images: {len(all_images)}")
        print(f"First created: {all_images[0].created_at}")
        print(f"Last created: {all_images[-1].created_at}")
        
        # Get unique users who requested this
        unique_users = list(set([img.user_id for img in all_images]))
        print(f"Unique users: {len(unique_users)}")
        
        # Simulate requests from different users
        print(f"\n{'='*60}")
        print("SIMULATING CACHE LOOKUPS")
        print("="*60)
        
        cache_hits = 0
        cache_misses = 0
        
        for i, user_id in enumerate(unique_users[:10]):  # Test first 10 users
            result = crud.find_cached_image(session, test_hash, user_id)
            
            if result:
                cache_hits += 1
                print(f"\n✅ User {user_id}: CACHE HIT")
                print(f"   Would serve image {result.id} (created {result.created_at})")
            else:
                cache_misses += 1
                print(f"\n❌ User {user_id}: CACHE MISS")
                
                # Check why
                user_images = [img for img in all_images if img.user_id == user_id]
                print(f"   This user has {len(user_images)} images with this hash")
        
        print(f"\n{'='*60}")
        print("RESULTS")
        print("="*60)
        print(f"\nCache hits: {cache_hits}")
        print(f"Cache misses: {cache_misses}")
        print(f"Hit rate: {cache_hits/(cache_hits+cache_misses)*100:.1f}%")
        
        if cache_hits > 0:
            print(f"\n✅ CACHE IS WORKING!")
            print(f"The cache lookup function works correctly.")
            print(f"If you're seeing 0 cache hits in production, it means:")
            print(f"  1. The cache lookup is not being called")
            print(f"  2. OR users are always requesting new unique prompts")
            print(f"  3. OR there's an issue with how prompts are being hashed")
        else:
            print(f"\n❌ CACHE NOT WORKING")
            print(f"Even with {len(all_images)} eligible images, no cache hits!")


if __name__ == "__main__":
    simulate_request()
