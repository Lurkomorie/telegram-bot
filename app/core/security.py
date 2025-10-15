"""
Security utilities for webhook verification
"""
import hmac
import hashlib
from app.settings import settings


def generate_hmac_signature(data: str) -> str:
    """
    Generate HMAC-SHA256 signature for webhook URLs
    
    Args:
        data: Data to sign (typically job_id)
    
    Returns:
        Hex-encoded HMAC signature
    """
    secret = settings.IMAGE_CALLBACK_SECRET.encode()
    message = data.encode()
    
    signature = hmac.new(secret, message, hashlib.sha256)
    return signature.hexdigest()


def verify_hmac_signature(data: str, provided_signature: str) -> bool:
    """
    Verify HMAC signature from webhook callback
    
    Args:
        data: Original data (job_id)
        provided_signature: Signature from query param
    
    Returns:
        True if signature is valid
    """
    expected_signature = generate_hmac_signature(data)
    return hmac.compare_digest(expected_signature, provided_signature)


def verify_webhook_signature(raw_body: bytes, provided_signature: str) -> bool:
    """
    Verify webhook signature using raw request body
    Alternative method if you want to sign the entire payload
    
    Args:
        raw_body: Raw request body bytes
        provided_signature: Signature from header or query param
    
    Returns:
        True if signature is valid
    """
    secret = settings.IMAGE_CALLBACK_SECRET.encode()
    expected = hmac.new(secret, raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, provided_signature)


