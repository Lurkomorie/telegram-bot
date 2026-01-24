"""
Check if recent images have Cloudflare URLs
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timedelta
from app.db.base import get_db
from app.db.models import ImageJob


def check_cloudflare_urls():
    """Check recent images for Cloudflare URLs"""
    
    five_hours_ago = datetime.utcnow() - timedelta(hours=5)
    
    with get_db() as session:
        recent_images = session.query(
            ImageJob.id,
            ImageJob.result_url,
            ImageJob.status,
            ImageJob.prompt_hash,
            ImageJob.created_at
        ).filter(
            ImageJob.created_at >= five_hours_ago,
            ImageJob.status == 'completed'
        ).order_by(ImageJob.created_at.desc()).limit(100).all()
        
        print(f"Checking last 100 completed images from last 5 hours...")
        print("="*60)
        
        cloudflare_count = 0
        binary_count = 0
        other_count = 0
        none_count = 0
        
        for img in recent_images:
            if img.result_url is None:
                none_count += 1
            elif img.result_url.startswith("https://imagedelivery.net/"):
                cloudflare_count += 1
            elif img.result_url.startswith("binary:"):
                binary_count += 1
            else:
                other_count += 1
                if other_count <= 5:  # Show first 5 examples
                    print(f"Other URL: {img.result_url[:80]}...")
        
        total = len(recent_images)
        print(f"\nTotal completed images checked: {total}")
        print(f"\nURL Types:")
        print(f"  - Cloudflare URLs: {cloudflare_count} ({cloudflare_count/total*100:.1f}%)")
        print(f"  - Binary placeholders: {binary_count} ({binary_count/total*100:.1f}%)")
        print(f"  - None/NULL: {none_count} ({none_count/total*100:.1f}%)")
        print(f"  - Other: {other_count} ({other_count/total*100:.1f}%)")
        
        print(f"\n{'='*60}")
        print("CACHE ELIGIBILITY")
        print("="*60)
        
        # Check cache eligibility (has hash + cloudflare URL + not blacklisted)
        cache_eligible = session.query(ImageJob).filter(
            ImageJob.created_at >= five_hours_ago,
            ImageJob.status == 'completed',
            ImageJob.prompt_hash.isnot(None),
            ImageJob.result_url.like("https://imagedelivery.net/%"),
            ImageJob.is_blacklisted == False
        ).count()
        
        total_completed = session.query(ImageJob).filter(
            ImageJob.created_at >= five_hours_ago,
            ImageJob.status == 'completed'
        ).count()
        
        print(f"\nCompleted images in last 5 hours: {total_completed}")
        print(f"Cache-eligible images: {cache_eligible} ({cache_eligible/total_completed*100:.1f}%)")
        print(f"\nCache-eligible means:")
        print(f"  ✓ Has prompt_hash")
        print(f"  ✓ Has Cloudflare URL (https://imagedelivery.net/...)")
        print(f"  ✓ Not blacklisted")


if __name__ == "__main__":
    check_cloudflare_urls()
