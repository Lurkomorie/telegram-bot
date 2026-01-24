"""
Delete images from Cloudflare CDN (background job).
Reads Cloudflare IDs from file created by cleanup_db_fast.py

Run with: nohup python -u scripts/cleanup_cloudflare.py > /tmp/cf_cleanup.log 2>&1 &
"""
import sys
import asyncio
import aiohttp
from pathlib import Path

sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.settings import settings

CF_IDS_FILE = "/tmp/cloudflare_ids_to_delete.txt"
BATCH_SIZE = 100
CONCURRENCY = 5  # Parallel requests
DELAY_BETWEEN_BATCHES = 1  # seconds


async def cleanup_cloudflare():
    """Delete images from Cloudflare - sequential but with reused session"""
    print("\n" + "="*60)
    print("CLOUDFLARE CLEANUP")
    print("="*60)
    
    # Read IDs from file
    try:
        with open(CF_IDS_FILE, 'r') as f:
            cf_ids = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"❌ File not found: {CF_IDS_FILE}")
        return
    
    # Deduplicate
    cf_ids = list(dict.fromkeys(cf_ids))
    print(f"Loaded {len(cf_ids)} unique IDs")
    
    api_token = settings.CLOUDFLARE_API_TOKEN
    account_id = settings.CLOUDFLARE_ACCOUNT_ID
    
    if not api_token or not account_id:
        print("❌ Cloudflare credentials not configured!")
        return
    
    headers = {"Authorization": f"Bearer {api_token}"}
    timeout = aiohttp.ClientTimeout(total=30)
    semaphore = asyncio.Semaphore(CONCURRENCY)
    
    total_deleted = 0
    total_failed = 0
    failed_ids = set()
    
    async def delete_one(session, cf_id):
        if cf_id in failed_ids:
            return False
        async with semaphore:
            url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/images/v1/{cf_id}"
            try:
                async with session.delete(url) as resp:
                    result = await resp.json()
                    if resp.status == 200 and result.get("success"):
                        return True
                    failed_ids.add(cf_id)
                    return False
            except:
                return False
    
    async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
        for i in range(0, len(cf_ids), BATCH_SIZE):
            batch = cf_ids[i:i + BATCH_SIZE]
            batch_num = i // BATCH_SIZE + 1
            
            print(f"\n📦 Batch {batch_num}: Deleting {len(batch)} images...")
            
            tasks = [delete_one(session, cf_id) for cf_id in batch]
            results = await asyncio.gather(*tasks)
            
            deleted = sum(1 for r in results if r)
            failed = sum(1 for r in results if not r)
            
            total_deleted += deleted
            total_failed += failed
            
            print(f"   ✅ Deleted: {deleted}, Failed: {failed}")
            print(f"   📊 Total: {total_deleted} deleted, {total_failed} failed")
            print(f"   📈 Progress: {i + len(batch)}/{len(cf_ids)} ({(i + len(batch)) * 100 // len(cf_ids)}%)")
            
            if i + BATCH_SIZE < len(cf_ids):
                print(f"   ⏳ Waiting {DELAY_BETWEEN_BATCHES}s...")
                await asyncio.sleep(DELAY_BETWEEN_BATCHES)
    
    print("\n" + "="*60)
    print("COMPLETE")
    print("="*60)
    print(f"Total deleted: {total_deleted}")
    print(f"Total failed: {total_failed}")
    
    try:
        Path(CF_IDS_FILE).unlink()
        print(f"🗑️ Removed {CF_IDS_FILE}")
    except:
        pass


if __name__ == "__main__":
    asyncio.run(cleanup_cloudflare())
