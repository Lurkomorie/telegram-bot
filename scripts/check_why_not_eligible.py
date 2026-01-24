"""
Check why recent images aren't cache-eligible
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timedelta
from app.db.base import get_db
from app.db.models import ImageJob


def check_eligibility():
    """Check why images aren't cache-eligible"""
    
    five_hours_ago = datetime.utcnow() - timedelta(hours=5)
    
    with get_db() as session:
        # Get recent completed images
        recent = session.query(ImageJob).filter(
            ImageJob.created_at >= five_hours_ago,
            ImageJob.status == 'completed',
            ImageJob.prompt_hash.isnot(None)
        ).order_by(ImageJob.created_at.desc()).limit(50).all()
        
        print(f"Checking {len(recent)} recent completed images with hashes...")
        print("="*60)
        
        eligible_count = 0
        not_eligible_reasons = {
            'no_url': 0,
            'wrong_url_type': 0,
            'blacklisted': 0
        }
        
        for img in recent:
            is_eligible = True
            reasons = []
            
            if not img.result_url:
                is_eligible = False
                reasons.append("no URL")
                not_eligible_reasons['no_url'] += 1
            elif not img.result_url.startswith('https://imagedelivery.net/'):
                is_eligible = False
                reasons.append(f"wrong URL: {img.result_url[:50]}")
                not_eligible_reasons['wrong_url_type'] += 1
            
            if img.is_blacklisted:
                is_eligible = False
                reasons.append("blacklisted")
                not_eligible_reasons['blacklisted'] += 1
            
            if is_eligible:
                eligible_count += 1
            else:
                if eligible_count + sum(not_eligible_reasons.values()) <= 10:
                    print(f"\n❌ Image {img.id}")
                    print(f"   Created: {img.created_at}")
                    print(f"   Reasons: {', '.join(reasons)}")
        
        print(f"\n{'='*60}")
        print("SUMMARY")
        print("="*60)
        print(f"\nTotal checked: {len(recent)}")
        print(f"Eligible: {eligible_count} ({eligible_count/len(recent)*100:.1f}%)")
        print(f"\nNot eligible reasons:")
        print(f"  - No URL: {not_eligible_reasons['no_url']}")
        print(f"  - Wrong URL type: {not_eligible_reasons['wrong_url_type']}")
        print(f"  - Blacklisted: {not_eligible_reasons['blacklisted']}")
        
        # Check what URL types exist
        if not_eligible_reasons['wrong_url_type'] > 0:
            print(f"\n{'='*60}")
            print("WRONG URL TYPES")
            print("="*60)
            
            wrong_urls = [img for img in recent if img.result_url and not img.result_url.startswith('https://imagedelivery.net/')]
            
            url_types = {}
            for img in wrong_urls[:10]:
                url_prefix = img.result_url[:30] if img.result_url else "None"
                url_types[url_prefix] = url_types.get(url_prefix, 0) + 1
            
            for url_type, count in url_types.items():
                print(f"  {url_type}... : {count}")


if __name__ == "__main__":
    check_eligibility()
