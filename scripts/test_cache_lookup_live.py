"""
Test cache lookup with actual data to see what's happening
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timedelta
from app.db.base import get_db
from app.db import crud
from app.db.models import ImageJob


def test_cache_lookup():
    """Test cache lookup with real data"""
    
    five_hours_ago = datetime.utcnow() - timedelta(hours=5)
    
    with get_db() as session:
        # Get a hash that was used multiple times recently
        recent_hash_query = session.query(
            ImageJob.prompt_hash,
            ImageJob.user_id
        ).filter(
            ImageJob.created_at >= five_hours_ago,
            ImageJob.prompt_hash.isnot(None),
            ImageJob.status == 'completed'
        ).first()
        
        if not recent_hash_query:
            print("No recent completed images with hash found")
            return
        
        test_hash = recent_hash_query.prompt_hash
        test_user = recent_hash_query.user_id
        
        print(f"Testing cache lookup:")
        print(f"  Hash: {test_hash[:16]}...")
        print(f"  User: {test_user}")
        print("="*60)
        
        # Count total images with this hash
        total_with_hash = session.query(ImageJob).filter(
            ImageJob.prompt_hash == test_hash
        ).count()
        
        print(f"\nTotal images with this hash: {total_with_hash}")
        
        # Count cache-eligible
        eligible = session.query(ImageJob).filter(
            ImageJob.prompt_hash == test_hash,
            ImageJob.status == "completed",
            ImageJob.result_url.like("https://imagedelivery.net/%"),
            ImageJob.is_blacklisted == False
        ).count()
        
        print(f"Cache-eligible images: {eligible}")
        
        # Now call the actual crud function
        print(f"\n{'='*60}")
        print("CALLING crud.find_cached_image()")
        print("="*60)
        
        result = crud.find_cached_image(session, test_hash, test_user)
        
        if result:
            print(f"\n✅ CACHE HIT!")
            print(f"  Image ID: {result.id}")
            print(f"  Created: {result.created_at}")
            print(f"  User: {result.user_id}")
            print(f"  URL: {result.result_url[:80]}...")
            print(f"  Status: {result.status}")
            print(f"  Blacklisted: {result.is_blacklisted}")
            print(f"  Cache serve count: {result.cache_serve_count}")
        else:
            print(f"\n❌ NO CACHE HIT")
            print("\nThis means either:")
            print("  1. No cache-eligible images exist")
            print("  2. All cache-eligible images have been shown to this user")
            print("  3. There's a bug in the query")
            
            # Let's check if it's #2
            from app.db.models import UserShownImage
            shown_count = session.query(UserShownImage).filter(
                UserShownImage.user_id == test_user
            ).count()
            
            print(f"\nImages shown to this user: {shown_count}")
            
            if shown_count == 0:
                print("❌ User has NO shown images tracked!")
                print("This means the NOT EXISTS check will always pass.")
                print("The problem must be elsewhere...")
                
                # Let's manually check each condition
                print(f"\nManually checking conditions:")
                
                # Get one eligible image
                sample = session.query(ImageJob).filter(
                    ImageJob.prompt_hash == test_hash,
                    ImageJob.status == "completed",
                    ImageJob.result_url.like("https://imagedelivery.net/%"),
                    ImageJob.is_blacklisted == False
                ).first()
                
                if sample:
                    print(f"\n✅ Found sample eligible image: {sample.id}")
                    print(f"   URL starts with: {sample.result_url[:50]}...")
                    print(f"   URL matches pattern: {sample.result_url.startswith('https://imagedelivery.net/')}")
                    
                    # Try the exact query from crud
                    from sqlalchemy import exists, and_
                    from app.db.models import UserShownImage
                    
                    not_shown = ~exists().where(
                        and_(
                            UserShownImage.user_id == test_user,
                            UserShownImage.image_job_id == ImageJob.id
                        )
                    )
                    
                    manual_result = session.query(ImageJob).filter(
                        ImageJob.prompt_hash == test_hash,
                        ImageJob.status == "completed",
                        ImageJob.result_url.like("https://imagedelivery.net/%"),
                        ImageJob.is_blacklisted == False,
                        not_shown
                    ).first()
                    
                    if manual_result:
                        print(f"\n✅ Manual query found: {manual_result.id}")
                        print("   So the query works, but crud.find_cached_image() doesn't?")
                    else:
                        print(f"\n❌ Manual query also found nothing")
                        print("   This is very strange...")


if __name__ == "__main__":
    test_cache_lookup()
