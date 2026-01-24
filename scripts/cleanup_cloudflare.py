"""
Delete images from Cloudflare CDN (background job).
Reads Cloudflare IDs from file created by cleanup_db_fast.py

Run with: nohup python -u scripts/cleanup_cloudflare.py > /tmp/cf_cleanup.log 2>&1 &
"""
import sys
import asyncio
import aiohttp
from pathlib import Path

# Unbuffered output
sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.settings import settings

CF_IDS_FILE = "/tmp/cloudflare_ids_to_delete.txt"
BATCH_SIZE = 50  # Process 50 images per batch
CONCURRENCY = 5  # 5 parallel requests at a time
DELAY_BETWEEN_BATCHES = 1.0  # Delay between batches


async def delete_single(
    session: aiohttp.ClientSession,
    semaphore: asyncio.Semaphore,
    image_id: str,
    account_id: str,
    failed_ids: set,
    errors_logged: set,
) -> bool:
    """Delete single image with semaphore for rate limiting"""
    # Skip if already known to be deleted/not found
    if image_id in failed_ids:
        return False
    
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/images/v1/{image_id}"
    
    async with semaphore:
        try:
            async with session.delete(url) as resp:
                result = await resp.json()
                if resp.status == 200 and result.get("success"):
                    return True
                
                error_msg = str(result.get('errors', [{}])[0].get('message', f'status={resp.status}'))
                
                # Image not found - mark as failed
                if "not found" in error_msg.lower() or resp.status == 404:
                    failed_ids.add(image_id)
                    return False
                
                # Log other errors (first few only)
                if error_msg not in errors_logged and len(errors_logged) < 3:
                    errors_logged.add(error_msg)
                    print(f"   ⚠️ Error: {error_msg}")
                return False
        except Exception as e:
            if str(e) not in errors_logged and len(errors_logged) < 3:
                errors_logged.add(str(e))
                print(f"   ❌ Exception: {e}")
            return False


async def cleanup_cloudflare():
    """Delete images from Cloudflare using IDs from file - FAST parallel version"""
    print("\n" + "="*60)
    print("CLOUDFLARE CLEANUP (FAST PARALLEL)")
    print("="*60)
    
    # Read IDs from file
    try:
        with open(CF_IDS_FILE, 'r') as f:
            cf_ids = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"❌ File not found: {CF_IDS_FILE}")
        print("   Run cleanup_db_fast.py first!")
        return
    
    # Deduplicate IDs
    cf_ids_unique = list(dict.fromkeys(cf_ids))
    print(f"Loaded {len(cf_ids)} IDs ({len(cf_ids_unique)} unique)")
    print(f"Batch size: {BATCH_SIZE}, Concurrency: {CONCURRENCY}")
    
    api_token = settings.CLOUDFLARE_API_TOKEN
    account_id = settings.CLOUDFLARE_ACCOUNT_ID
    
    if not api_token or not account_id:
        print("❌ Cloudflare credentials not configured!")
        return
    
    total_deleted = 0
    total_failed = 0
    failed_ids: set = set()  # Track failed IDs to skip duplicates
    errors_logged: set = set()  # Track logged errors to avoid spam
    
    headers = {"Authorization": f"Bearer {api_token}"}
    timeout = aiohttp.ClientTimeout(total=30)
    semaphore = asyncio.Semaphore(CONCURRENCY)
    
    # Use single session for all requests (much faster)
    async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
        for i in range(0, len(cf_ids_unique), BATCH_SIZE):
            batch = cf_ids_unique[i:i + BATCH_SIZE]
            batch_num = i // BATCH_SIZE + 1
            
            print(f"\n📦 Batch {batch_num}: Deleting {len(batch)} images...")
            
            # Delete all images in batch in parallel
            tasks = [
                delete_single(session, semaphore, cf_id, account_id, failed_ids, errors_logged)
                for cf_id in batch
            ]
            results = await asyncio.gather(*tasks)
            
            deleted = sum(1 for r in results if r)
            failed = sum(1 for r in results if not r)
            
            total_deleted += deleted
            total_failed += failed
            
            progress = (i + len(batch)) / len(cf_ids_unique) * 100
            print(f"   ✅ Deleted: {deleted}, Failed: {failed}")
            print(f"   📊 Total: {total_deleted} deleted, {total_failed} failed")
            print(f"   📈 Progress: {i + len(batch)}/{len(cf_ids_unique)} ({progress:.1f}%)")
            
            if i + BATCH_SIZE < len(cf_ids_unique):
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
