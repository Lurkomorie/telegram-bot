"""
Image processing utilities
Handles color profile stripping, blurring, and image optimization for Telegram
"""
from io import BytesIO
from typing import Optional
from PIL import Image, ImageFilter


def strip_color_profile(image_data: bytes) -> bytes:
    """
    Strip ICC color profile from PNG image to prevent color distortion in Telegram.
    
    Telegram's image renderer (especially on mobile) can misinterpret embedded ICC profiles,
    causing yellowish tints. This function removes all color profile metadata while preserving
    image quality and dimensions.
    
    Args:
        image_data: Raw PNG image bytes
    
    Returns:
        Clean PNG bytes without embedded color profiles
    
    Raises:
        Exception: If image processing fails
    """
    try:
        # Load image from bytes
        img = Image.open(BytesIO(image_data))
        
        # Preserve the color mode (RGB or RGBA)
        # Don't convert unnecessarily - keep transparency if present
        original_mode = img.mode
        
        # Remove ICC profile and all color-related metadata
        # Create new image without the profile
        if "icc_profile" in img.info:
            print(f"[IMAGE-UTILS] Stripping ICC profile from {original_mode} image")
        
        # Create a new image to strip metadata
        # Keep the original mode to preserve transparency
        clean_img = Image.new(original_mode, img.size)
        clean_img.putdata(list(img.getdata()))
        
        # Save to bytes with maximum quality (compress_level=0 means no compression)
        output = BytesIO()
        clean_img.save(
            output,
            format='PNG',
            compress_level=0,  # No compression for maximum quality
            optimize=False     # Don't optimize, preserve quality
        )
        
        output.seek(0)
        clean_bytes = output.read()
        
        print(f"[IMAGE-UTILS] ✅ Color profile stripped: {len(image_data)} → {len(clean_bytes)} bytes")
        
        return clean_bytes
        
    except Exception as e:
        print(f"[IMAGE-UTILS] ❌ Failed to strip color profile: {e}")
        raise


def strip_color_profile_safe(image_data: bytes) -> bytes:
    """
    Safe wrapper that returns original data if processing fails.
    
    Args:
        image_data: Raw PNG image bytes
    
    Returns:
        Processed PNG bytes, or original bytes if processing fails
    """
    try:
        return strip_color_profile(image_data)
    except Exception as e:
        print(f"[IMAGE-UTILS] ⚠️  Falling back to original image due to error: {e}")
        return image_data


def blur_image(image_data: bytes, blur_radius: int = 30) -> bytes:
    """
    Apply Gaussian blur to an image for paywall preview.
    
    Args:
        image_data: Raw image bytes (PNG or JPEG)
        blur_radius: Blur intensity (default 30 for heavy blur)
    
    Returns:
        Blurred image as PNG bytes
    """
    try:
        img = Image.open(BytesIO(image_data))
        
        # Convert to RGB if necessary (handle RGBA, P mode, etc.)
        if img.mode in ('RGBA', 'LA', 'P'):
            # Create white background for transparency
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Apply strong Gaussian blur
        blurred = img.filter(ImageFilter.GaussianBlur(radius=blur_radius))
        
        # Save to bytes
        output = BytesIO()
        blurred.save(output, format='JPEG', quality=85)
        output.seek(0)
        
        print(f"[IMAGE-UTILS] 🔒 Image blurred with radius {blur_radius}")
        return output.read()
        
    except Exception as e:
        print(f"[IMAGE-UTILS] ❌ Failed to blur image: {e}")
        raise


def blur_image_safe(image_data: bytes, blur_radius: int = 30) -> Optional[bytes]:
    """
    Safe wrapper that returns None if blurring fails.
    
    Args:
        image_data: Raw image bytes
        blur_radius: Blur intensity
    
    Returns:
        Blurred image bytes, or None if processing fails
    """
    try:
        return blur_image(image_data, blur_radius)
    except Exception as e:
        print(f"[IMAGE-UTILS] ⚠️  Blur failed: {e}")
        return None









