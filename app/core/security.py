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


def validate_telegram_webapp_data(init_data: str) -> bool:
    """
    Validate Telegram Web App init data signature
    
    The init data is a URL-encoded string of key=value pairs.
    Telegram signs this data with the bot token.
    
    Algorithm (from Telegram docs):
    1. Parse init_data as URL query string
    2. Sort all key-value pairs alphabetically by key (except 'hash')
    3. Create data_check_string: key=value pairs joined with \n
    4. Create secret_key: HMAC-SHA256 of "WebAppData" with bot token
    5. Create hash: HMAC-SHA256 of data_check_string with secret_key
    6. Compare with provided hash
    
    Args:
        init_data: The initData string from Telegram WebApp
    
    Returns:
        True if signature is valid, False otherwise
    """
    if not init_data:
        return False
    
    try:
        # Parse the init_data
        from urllib.parse import parse_qsl
        parsed = dict(parse_qsl(init_data))
        
        # Extract hash
        provided_hash = parsed.pop('hash', None)
        if not provided_hash:
            return False
        
        # Sort parameters alphabetically and create data_check_string
        data_check_string = '\n'.join(
            f"{k}={v}" for k, v in sorted(parsed.items())
        )
        
        # Create secret key: HMAC-SHA256("WebAppData", bot_token)
        secret_key = hmac.new(
            key=b"WebAppData",
            msg=settings.BOT_TOKEN.encode(),
            digestmod=hashlib.sha256
        ).digest()
        
        # Create hash: HMAC-SHA256(data_check_string, secret_key)
        calculated_hash = hmac.new(
            key=secret_key,
            msg=data_check_string.encode(),
            digestmod=hashlib.sha256
        ).hexdigest()
        
        # Compare hashes
        return hmac.compare_digest(calculated_hash, provided_hash)
    
    except Exception as e:
        print(f"[WEBAPP-AUTH] Validation error: {e}")
        return False


