"""
Delete images from Cloudflare CDN (background job).
Reads Cloudflare IDs from file created by cleanup_db_fast.py

Run with: nohup python scripts/cleanup_cloudflare.py > /tmp/cf_cleanup.log 2>&1 &
"""
import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.cloudflare_upload import delete_from_cloudflare

CF_IDS_FILE = "/tmp/cloudflare_ids_to_delete.txt"
BATCH_SIZE = 50  # Cloudflare rate limit friendly
DELAY_BETWEEN_BATCHES = 2  # seconds


async def cleanup_cloudflare():
    """Delete images from Cloudflare using IDs from file"""
    print("\n" + "="*60)
    print("CLOUDFLARE CLEANUP")
    print("="*60)
    
    # Read IDs from file
    try:
        with open(CF_IDS_FILE, 'r') as f:
            cf_ids = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"❌ File not found: {CF_IDS_FILE}")
        print("   Run cleanup_db_fast.py first!")
        return
    
    print(f"Loaded {len(cf_ids)} Cloudflare IDs")
    print(f"Batch size: {BATCH_SIZE}")
    print(f"Delay: {DELAY_BETWEEN_BATCHES}s")
    
    total_deleted = 0
    total_failed = 0
    batch_num = 0
    
    for i in range(0, len(cf_ids), BATCH_SIZE):
        batch_num += 1
        batch = cf_ids[i:i + BATCH_SIZE]
        
        print(f"\n📦 Batch {batch_num}: Deleting {len(batch)} from Cloudflare...")
        
        deleted = 0
        failed = 0
        
        for cf_id in batch:
            success = await delete_from_cloudflare(cf_id)
            if success:
                deleted += 1
            else:
                failed += 1
        
        total_deleted += deleted
        total_failed += failed
        
        print(f"   ✅ Deleted: {deleted}, Failed: {failed}")
        print(f"   📊 Total: {total_deleted} deleted, {total_failed} failed")
        print(f"   📈 Progress: {i + len(batch)}/{len(cf_ids)} ({(i + len(batch)) * 100 // len(cf_ids)}%)")
        
        if i + BATCH_SIZE < len(cf_ids):
            print(f"   ⏳ Waiting {DELAY_BETWEEN_BATCHES}s...")
            await asyncio.sleep(DELAY_BETWEEN_BATCHES)
    
    print("\n" + "="*60)
    print("CLOUDFLARE CLEANUP COMPLETE")
    print("="*60)
    print(f"Total deleted: {total_deleted}")
    print(f"Total failed: {total_failed}")
    
    # Remove the IDs file
    try:
        Path(CF_IDS_FILE).unlink()
        print(f"🗑️  Removed {CF_IDS_FILE}")
    except:
        pass


if __name__ == "__main__":
    asyncio.run(cleanup_cloudflare())
