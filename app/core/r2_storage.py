"""
Cloudflare R2 storage helpers for uploads.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Optional

import boto3
from botocore.config import Config

from app.settings import settings


def is_r2_configured() -> bool:
    return all(
        [
            settings.R2_ACCESS_KEY_ID,
            settings.R2_SECRET_ACCESS_KEY,
            settings.R2_BUCKET_NAME,
            settings.R2_ENDPOINT_URL,
        ]
    )


def _normalized_prefix() -> str:
    prefix = (settings.R2_UPLOADS_PREFIX or "").strip("/")
    return prefix


def build_r2_key(*, filename: str) -> str:
    prefix = _normalized_prefix()
    return f"{prefix}/{filename}" if prefix else filename


@lru_cache(maxsize=1)
def get_r2_client():
    if not is_r2_configured():
        raise ValueError("R2 is not configured (missing credentials or endpoint)")
    return boto3.client(
        "s3",
        endpoint_url=settings.R2_ENDPOINT_URL,
        aws_access_key_id=settings.R2_ACCESS_KEY_ID,
        aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
        region_name="auto",
        config=Config(signature_version="s3v4"),
    )


def upload_bytes_to_r2(*, key: str, data: bytes, content_type: Optional[str]) -> None:
    client = get_r2_client()
    put_params = {"Bucket": settings.R2_BUCKET_NAME, "Key": key, "Body": data}
    if content_type:
        put_params["ContentType"] = content_type
    client.put_object(**put_params)


def build_r2_public_url(*, key: str) -> str:
    if not settings.R2_PUBLIC_BASE_URL:
        raise ValueError("R2_PUBLIC_BASE_URL is not set for public URLs")
    base = settings.R2_PUBLIC_BASE_URL.rstrip("/")
    return f"{base}/{key}"


def build_r2_signed_url(*, key: str, expires_seconds: Optional[int] = None) -> str:
    client = get_r2_client()
    expires = expires_seconds or settings.R2_URL_EXPIRES_SECONDS
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.R2_BUCKET_NAME, "Key": key},
        ExpiresIn=expires,
    )


def build_r2_object_url(*, key: str) -> str:
    if settings.R2_SIGNED_URLS:
        return build_r2_signed_url(key=key)
    return build_r2_public_url(key=key)
