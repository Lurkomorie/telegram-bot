"""
Cloudflare Images upload service for analytics
Uploads images to Cloudflare CDN for permanent archival
"""
import asyncio
from typing import Optional
from app.settings import settings


# Configuration
CLOUDFLARE_CONFIG = {
    "API_TOKEN": settings.CLOUDFLARE_API_TOKEN,
    "ACCOUNT_ID": settings.CLOUDFLARE_ACCOUNT_ID,
    "ACCOUNT_HASH": settings.CLOUDFLARE_ACCOUNT_HASH,
    "REQUIRE_SIGNED_URLS": False,
}

UPLOAD_CONFIG = {
    "MAX_RETRIES": 3,
    "TIMEOUT_MS": 30000,
    "RETRY_DELAY_MS": 2000,
    "MAX_FILE_SIZE": 10 * 1024 * 1024,  # 10MB
}


class UploadResult:
    """Result of Cloudflare upload"""
    def __init__(self, success: bool, image_id: str = None, image_url: str = None, error: str = None):
        self.success = success
        self.image_id = image_id
        self.image_url = image_url
        self.error = error


def build_cloudflare_image_url(image_id: str) -> str:
    """Build Cloudflare CDN URL for image"""
    account_hash = CLOUDFLARE_CONFIG["ACCOUNT_HASH"]
    return f"https://imagedelivery.net/{account_hash}/{image_id}/public"


def is_retryable_error(error: Exception) -> bool:
    """Check if error is retryable"""
    error_msg = str(error).lower()
    
    # Network errors are retryable
    if any(keyword in error_msg for keyword in ['timeout', 'connection', 'network', 'aborted']):
        return True
    
    # Server errors (5xx) are retryable
    if '5' in error_msg and ('server' in error_msg or 'error' in error_msg):
        return True
    
    # Client errors (4xx) are not retryable
    if any(keyword in error_msg for keyword in ['400', '401', '403', '404', '429']):
        return False
    
    return True


async def upload_to_cloudflare_tg(
    image_url_or_bytes: str | bytes,
    filename: str,
    max_retries: int = None,
    timeout_ms: int = None,
    retry_delay_ms: int = None,
) -> UploadResult:
    """
    Upload image to Cloudflare Images for analytics archival
    
    Args:
        image_url_or_bytes: Either a URL string or binary image data
        filename: Filename for the upload
        max_retries: Maximum number of retry attempts
        timeout_ms: Timeout in milliseconds
        retry_delay_ms: Delay between retries in milliseconds
    
    Returns:
        UploadResult with success status and image URL or error message
    """
    import aiohttp
    from io import BytesIO
    
    if max_retries is None:
        max_retries = UPLOAD_CONFIG["MAX_RETRIES"]
    if timeout_ms is None:
        timeout_ms = UPLOAD_CONFIG["TIMEOUT_MS"]
    if retry_delay_ms is None:
        retry_delay_ms = UPLOAD_CONFIG["RETRY_DELAY_MS"]
    
    last_error: Optional[Exception] = None
    
    for attempt in range(1, max_retries + 1):
        try:
            api_token = CLOUDFLARE_CONFIG["API_TOKEN"]
            account_id = CLOUDFLARE_CONFIG["ACCOUNT_ID"]
            
            if not api_token or not account_id:
                raise ValueError("Cloudflare API credentials not configured")
            
            print(f"[CLOUDFLARE] Uploading {filename}... (attempt {attempt}/{max_retries})")
            
            # Prepare image data
            if isinstance(image_url_or_bytes, bytes):
                # Already have binary data
                image_data = image_url_or_bytes
                content_type = "image/png"
            else:
                # Download from URL
                timeout = aiohttp.ClientTimeout(total=timeout_ms / 1000)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(image_url_or_bytes) as response:
                        if not response.ok:
                            raise Exception(f"Failed to download image: {response.status}")
                        image_data = await response.read()
                        content_type = response.headers.get('content-type', 'image/png')
            
            # Validate file size
            if len(image_data) > UPLOAD_CONFIG["MAX_FILE_SIZE"]:
                raise ValueError(
                    f"File size {len(image_data)} bytes exceeds maximum {UPLOAD_CONFIG['MAX_FILE_SIZE']} bytes"
                )
            
            # Prepare form data
            form_data = aiohttp.FormData()
            form_data.add_field(
                'file',
                BytesIO(image_data),
                filename=filename,
                content_type=content_type
            )
            form_data.add_field(
                'requireSignedURLs',
                str(CLOUDFLARE_CONFIG["REQUIRE_SIGNED_URLS"]).lower()
            )
            
            # Upload to Cloudflare
            upload_url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/images/v1"
            headers = {
                "Authorization": f"Bearer {api_token}",
            }
            
            timeout = aiohttp.ClientTimeout(total=timeout_ms / 1000)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(upload_url, headers=headers, data=form_data) as response:
                    result = await response.json()
                    
                    if not response.ok:
                        error_msg = result.get('errors', [{}])[0].get('message', 'Unknown error')
                        raise Exception(f"Cloudflare upload failed: {error_msg}")
                    
                    image_id = result.get('result', {}).get('id')
                    if not image_id:
                        raise Exception("No image ID returned from Cloudflare")
                    
                    final_image_url = build_cloudflare_image_url(image_id)
                    
                    print(f"[CLOUDFLARE] ✅ Upload successful on attempt {attempt}: {image_id}")
                    
                    return UploadResult(
                        success=True,
                        image_id=image_id,
                        image_url=final_image_url
                    )
        
        except Exception as error:
            last_error = error
            print(f"[CLOUDFLARE] ❌ Upload attempt {attempt}/{max_retries} failed: {error}")
            
            # Check if retryable
            is_retryable = is_retryable_error(error)
            
            if attempt == max_retries or not is_retryable:
                print(f"[CLOUDFLARE] 💥 Upload failed after {attempt} attempts. Final error: {error}")
                break
            
            # Exponential backoff with jitter
            import random
            delay = (retry_delay_ms * (2 ** (attempt - 1)) + random.random() * 1000) / 1000
            print(f"[CLOUDFLARE] ⏳ Retrying in {delay:.1f}s...")
            await asyncio.sleep(delay)
    
    return UploadResult(
        success=False,
        error=str(last_error) if last_error else "Upload failed after all retry attempts"
    )


def extract_image_id_from_url(result_url: str) -> Optional[str]:
    """Extract image_id from Cloudflare URL: https://imagedelivery.net/{hash}/{image_id}/public"""
    if not result_url or "imagedelivery.net" not in result_url:
        return None
    parts = result_url.split("/")
    # URL format: https://imagedelivery.net/{account_hash}/{image_id}/{variant}
    # parts: ['https:', '', 'imagedelivery.net', '{hash}', '{image_id}', '{variant}']
    if len(parts) >= 5:
        return parts[-2]  # image_id is second to last (before variant like 'public' or 'admin')
    return None


async def delete_from_cloudflare(image_id: str, timeout_ms: int = 10000) -> bool:
    """
    Delete image from Cloudflare CDN
    
    Args:
        image_id: Cloudflare image ID to delete
        timeout_ms: Timeout in milliseconds
    
    Returns:
        True if deletion was successful, False otherwise
    """
    import aiohttp
    
    api_token = CLOUDFLARE_CONFIG["API_TOKEN"]
    account_id = CLOUDFLARE_CONFIG["ACCOUNT_ID"]
    
    if not api_token or not account_id:
        print(f"[CLOUDFLARE] ⚠️ Cannot delete {image_id}: credentials not configured")
        return False
    
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/images/v1/{image_id}"
    headers = {"Authorization": f"Bearer {api_token}"}
    
    try:
        timeout = aiohttp.ClientTimeout(total=timeout_ms / 1000)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.delete(url, headers=headers) as resp:
                result = await resp.json()
                if resp.status == 200 and result.get("success"):
                    print(f"[CLOUDFLARE] 🗑️ Deleted image {image_id}")
                    return True
                else:
                    error_msg = result.get('errors', [{}])[0].get('message', 'Unknown error')
                    print(f"[CLOUDFLARE] ⚠️ Failed to delete {image_id}: {error_msg}")
                    return False
    except Exception as e:
        print(f"[CLOUDFLARE] ❌ Error deleting {image_id}: {e}")
        return False

