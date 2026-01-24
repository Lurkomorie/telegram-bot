"""
Check recent images (last 5 hours) for hash presence and cache hit potential
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timedelta
from collections import defaultdict
from sqlalchemy import func, and_
from app.db.base import get_db
from app.db.models import ImageJob


def analyze_recent_images():
    """Analyze images from the last 5 hours"""
    
    # Calculate time threshold (5 hours ago)
    five_hours_ago = datetime.utcnow() - timedelta(hours=5)
    
    print(f"Analyzing images created after: {five_hours_ago.isoformat()}")
    print("="*60)
    
    with get_db() as session:
        # Get all images from last 5 hours
        recent_images = session.query(
            ImageJob.id,
            ImageJob.prompt_hash,
            ImageJob.status,
            ImageJob.created_at,
            ImageJob.cache_serve_count,
            ImageJob.refresh_count,
            ImageJob.is_blacklisted
        ).filter(
            ImageJob.created_at >= five_hours_ago
        ).order_by(ImageJob.created_at.desc()).all()
        
        total_recent = len(recent_images)
        print(f"\nTotal images in last 5 hours: {total_recent}")
        
        if total_recent == 0:
            print("No images found in the last 5 hours.")
            return
        
        # Analyze hash presence
        with_hash = sum(1 for img in recent_images if img.prompt_hash is not None)
        without_hash = total_recent - with_hash
        
        print(f"\nHash Analysis:")
        print(f"  - Images WITH hash: {with_hash} ({with_hash/total_recent*100:.1f}%)")
        print(f"  - Images WITHOUT hash: {without_hash} ({without_hash/total_recent*100:.1f}%)")
        
        # Status breakdown
        status_counts = defaultdict(int)
        for img in recent_images:
            status_counts[img.status] += 1
        
        print(f"\nStatus Breakdown:")
        for status, count in status_counts.items():
            print(f"  - {status}: {count} ({count/total_recent*100:.1f}%)")
        
        # Cache analysis for images with hash
        if with_hash > 0:
            print(f"\n{'='*60}")
            print("CACHE POTENTIAL ANALYSIS")
            print("="*60)
            
            # Group by hash to find potential cache hits
            hash_groups = defaultdict(list)
            for img in recent_images:
                if img.prompt_hash:
                    hash_groups[img.prompt_hash].append({
                        'id': str(img.id),
                        'created_at': img.created_at,
                        'status': img.status,
                        'cache_serve_count': img.cache_serve_count,
                        'refresh_count': img.refresh_count,
                        'is_blacklisted': img.is_blacklisted
                    })
            
            # Find hashes that appear multiple times in recent period
            duplicate_hashes = {h: imgs for h, imgs in hash_groups.items() if len(imgs) > 1}
            
            print(f"\nRecent duplicate hashes: {len(duplicate_hashes)}")
            if duplicate_hashes:
                total_duplicates = sum(len(imgs) for imgs in duplicate_hashes.values())
                potential_saves = total_duplicates - len(duplicate_hashes)
                print(f"Total images with duplicate hashes: {total_duplicates}")
                print(f"Potential cache hits (if first was cached): {potential_saves}")
                
                # Show top 5 most duplicated
                sorted_dupes = sorted(duplicate_hashes.items(), key=lambda x: len(x[1]), reverse=True)
                print(f"\nTop 5 most duplicated hashes in last 5 hours:")
                for i, (hash_val, imgs) in enumerate(sorted_dupes[:5], 1):
                    print(f"\n{i}. Hash: {hash_val[:16]}... (used {len(imgs)} times)")
                    print(f"   Times:")
                    for img in imgs[:3]:  # Show first 3
                        print(f"     - {img['created_at'].strftime('%H:%M:%S')} - {img['status']}")
                    if len(imgs) > 3:
                        print(f"     ... and {len(imgs) - 3} more")
            
            # Check if any recent hashes existed before 5 hours ago
            print(f"\n{'='*60}")
            print("HISTORICAL CACHE HIT ANALYSIS")
            print("="*60)
            
            recent_hashes = [img.prompt_hash for img in recent_images if img.prompt_hash]
            unique_recent_hashes = list(set(recent_hashes))
            
            print(f"\nChecking {len(unique_recent_hashes)} unique hashes against historical data...")
            
            # Find older images with same hashes
            historical_matches = session.query(
                ImageJob.prompt_hash,
                func.count(ImageJob.id).label('count'),
                func.min(ImageJob.created_at).label('first_seen')
            ).filter(
                and_(
                    ImageJob.prompt_hash.in_(unique_recent_hashes),
                    ImageJob.created_at < five_hours_ago,
                    ImageJob.status == 'completed',
                    ImageJob.is_blacklisted == False
                )
            ).group_by(ImageJob.prompt_hash).all()
            
            if historical_matches:
                print(f"\nFound {len(historical_matches)} hashes that existed before!")
                
                # Count how many recent images could have been cache hits
                cacheable_count = 0
                for img in recent_images:
                    if img.prompt_hash:
                        for match in historical_matches:
                            if match.prompt_hash == img.prompt_hash:
                                cacheable_count += 1
                                break
                
                print(f"Recent images that could have been served from cache: {cacheable_count}")
                print(f"Actual cache hit rate: {cacheable_count/total_recent*100:.1f}%")
                
                # Show some examples
                print(f"\nTop 5 historical matches:")
                sorted_historical = sorted(historical_matches, key=lambda x: x.count, reverse=True)
                for i, match in enumerate(sorted_historical[:5], 1):
                    # Count recent uses
                    recent_uses = sum(1 for img in recent_images if img.prompt_hash == match.prompt_hash)
                    print(f"\n{i}. Hash: {match.prompt_hash[:16]}...")
                    print(f"   First seen: {match.first_seen.strftime('%Y-%m-%d %H:%M:%S')}")
                    print(f"   Historical uses: {match.count}")
                    print(f"   Recent uses (last 5h): {recent_uses}")
                    print(f"   Potential savings: {recent_uses} generations")
            else:
                print("\nNo historical matches found - all recent hashes are new!")
        
        # Cache serve statistics
        print(f"\n{'='*60}")
        print("CACHE SERVE STATISTICS")
        print("="*60)
        
        served_from_cache = sum(1 for img in recent_images if img.cache_serve_count > 0)
        total_cache_serves = sum(img.cache_serve_count for img in recent_images)
        
        print(f"\nImages that have been served from cache: {served_from_cache}")
        print(f"Total cache serve count: {total_cache_serves}")
        
        if served_from_cache > 0:
            print(f"\nTop 5 most cached images:")
            sorted_by_cache = sorted(recent_images, key=lambda x: x.cache_serve_count, reverse=True)
            for i, img in enumerate(sorted_by_cache[:5], 1):
                if img.cache_serve_count > 0:
                    print(f"{i}. Served {img.cache_serve_count} times (hash: {img.prompt_hash[:16] if img.prompt_hash else 'None'}...)")
        
        # Refresh statistics
        refreshed_images = sum(1 for img in recent_images if img.refresh_count > 0)
        total_refreshes = sum(img.refresh_count for img in recent_images)
        
        print(f"\nImages that were refreshed: {refreshed_images}")
        print(f"Total refresh count: {total_refreshes}")
        
        # Blacklisted images
        blacklisted = sum(1 for img in recent_images if img.is_blacklisted)
        print(f"\nBlacklisted images: {blacklisted}")


if __name__ == "__main__":
    analyze_recent_images()
