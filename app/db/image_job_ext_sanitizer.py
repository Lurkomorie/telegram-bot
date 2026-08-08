"""
Helpers for sanitizing image job ext payloads.

Prevents large blob-like values from being stored in Postgres JSONB.
"""
import json
import os
import re
from typing import Any, Dict, List, Tuple


DEFAULT_MAX_IMAGE_JOB_EXT_VALUE_BYTES = int(
    os.getenv("IMAGE_JOB_EXT_MAX_VALUE_BYTES", "65536")
)
FORBIDDEN_IMAGE_JOB_EXT_KEYS = {"blurred_original_data"}

_BASE64_CHARS_RE = re.compile(r"^[A-Za-z0-9+/=\s]+$")


def _is_blob_like_string(value: str) -> bool:
    if len(value) < 4096:
        return False

    if value.startswith("data:image/"):
        return True

    prefix = value[:128]
    if (
        prefix.startswith("iVBORw0KGgo")
        or prefix.startswith("/9j/")
        or prefix.startswith("R0lGOD")
    ):
        return True

    sample = value[:4096].replace("\n", "").replace("\r", "")
    if not sample:
        return False

    return bool(_BASE64_CHARS_RE.match(sample)) and len(sample) >= 2048


def _is_oversized_blob_like(value: Any, max_value_bytes: int) -> bool:
    if isinstance(value, (bytes, bytearray, memoryview)):
        return len(value) > max_value_bytes

    if isinstance(value, str):
        size = len(value.encode("utf-8", errors="ignore"))
        if size <= max_value_bytes:
            return False
        return _is_blob_like_string(value) or value.startswith("data:")

    if isinstance(value, (list, dict)):
        try:
            serialized = json.dumps(value, ensure_ascii=False)
        except Exception:
            return False
        return len(serialized.encode("utf-8", errors="ignore")) > (max_value_bytes * 4)

    return False


def sanitize_image_job_ext(
    ext: Any,
    *,
    max_value_bytes: int = DEFAULT_MAX_IMAGE_JOB_EXT_VALUE_BYTES,
) -> Tuple[Dict[str, Any], List[str]]:
    """
    Remove forbidden / blob-like keys from ImageJob.ext.

    Returns:
        (sanitized_ext, removed_keys)
    """
    if not isinstance(ext, dict):
        if ext:
            return {}, ["__non_dict_ext__"]
        return {}, []

    sanitized: Dict[str, Any] = {}
    removed: List[str] = []

    for key, value in ext.items():
        if key in FORBIDDEN_IMAGE_JOB_EXT_KEYS:
            removed.append(key)
            continue
        if _is_oversized_blob_like(value, max_value_bytes=max_value_bytes):
            removed.append(key)
            continue
        sanitized[key] = value

    return sanitized, removed
