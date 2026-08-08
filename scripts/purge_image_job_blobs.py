"""
Purge large blob-like payloads from image_jobs.ext.

Usage:
  python scripts/purge_image_job_blobs.py                     # dry-run
  python scripts/purge_image_job_blobs.py --execute          # apply changes
  python scripts/purge_image_job_blobs.py --execute --batch-size 500 --max-rows 20000
"""
import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from sqlalchemy import and_, or_
from sqlalchemy.orm.attributes import flag_modified

# Add project root to path for local imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.base import get_db  # noqa: E402
from app.db.models import ImageJob  # noqa: E402
from app.db.image_job_ext_sanitizer import (  # noqa: E402
    DEFAULT_MAX_IMAGE_JOB_EXT_VALUE_BYTES,
    sanitize_image_job_ext,
)


def _json_size_bytes(value) -> int:
    try:
        return len(json.dumps(value, ensure_ascii=False).encode("utf-8", errors="ignore"))
    except Exception:
        return 0


def run_purge(
    *,
    execute: bool,
    batch_size: int,
    max_rows: Optional[int],
    threshold_bytes: int,
) -> None:
    scanned = 0
    changed = 0
    removed_bytes_total = 0
    removed_keys_stats: dict[str, int] = {}

    last_created_at = None
    last_id = None

    print("=" * 72)
    print("ImageJob ext blob purge")
    print("=" * 72)
    print(f"Mode: {'EXECUTE' if execute else 'DRY-RUN'}")
    print(f"Batch size: {batch_size}")
    print(f"Threshold bytes: {threshold_bytes}")
    if max_rows:
        print(f"Max rows: {max_rows}")
    print()

    with get_db() as db:
        while True:
            if max_rows is not None and scanned >= max_rows:
                break

            query = db.query(ImageJob).order_by(ImageJob.created_at.asc(), ImageJob.id.asc())
            if last_created_at is not None and last_id is not None:
                query = query.filter(
                    or_(
                        ImageJob.created_at > last_created_at,
                        and_(ImageJob.created_at == last_created_at, ImageJob.id > last_id),
                    )
                )

            current_batch_size = batch_size
            if max_rows is not None:
                current_batch_size = min(current_batch_size, max_rows - scanned)

            rows = query.limit(current_batch_size).all()
            if not rows:
                break

            batch_changed = 0
            for row in rows:
                scanned += 1

                before_ext = row.ext or {}
                before_size = _json_size_bytes(before_ext)

                sanitized_ext, removed_keys = sanitize_image_job_ext(
                    before_ext,
                    max_value_bytes=threshold_bytes,
                )

                if removed_keys:
                    changed += 1
                    batch_changed += 1
                    after_size = _json_size_bytes(sanitized_ext)
                    removed_bytes_total += max(before_size - after_size, 0)

                    for key in removed_keys:
                        removed_keys_stats[key] = removed_keys_stats.get(key, 0) + 1

                    if execute:
                        row.ext = sanitized_ext
                        flag_modified(row, "ext")

                if max_rows is not None and scanned >= max_rows:
                    break

            if execute and batch_changed > 0:
                db.commit()

            last_created_at = rows[-1].created_at
            last_id = rows[-1].id

            print(
                f"Scanned: {scanned:,} | Changed: {changed:,} | "
                f"Estimated bytes removed: {removed_bytes_total:,}"
            )

    print()
    print("=" * 72)
    print("Summary")
    print("=" * 72)
    print(f"Scanned rows: {scanned:,}")
    print(f"Rows with removed blob-like keys: {changed:,}")
    print(f"Estimated bytes removed from ext: {removed_bytes_total:,}")
    if removed_keys_stats:
        print("Removed keys:")
        for key, count in sorted(removed_keys_stats.items(), key=lambda x: (-x[1], x[0])):
            print(f"  - {key}: {count:,}")
    else:
        print("Removed keys: none")

    if not execute:
        print()
        print("Dry-run complete. Re-run with --execute to apply changes.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Purge large blob-like payloads from image_jobs.ext")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Apply updates. Without this flag, runs in dry-run mode.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="Rows per batch (default: 1000)",
    )
    parser.add_argument(
        "--max-rows",
        type=int,
        default=None,
        help="Optional cap on scanned rows",
    )
    parser.add_argument(
        "--threshold-bytes",
        type=int,
        default=DEFAULT_MAX_IMAGE_JOB_EXT_VALUE_BYTES,
        help=f"Oversized value threshold in bytes (default: {DEFAULT_MAX_IMAGE_JOB_EXT_VALUE_BYTES})",
    )
    args = parser.parse_args()

    run_purge(
        execute=args.execute,
        batch_size=args.batch_size,
        max_rows=args.max_rows,
        threshold_bytes=args.threshold_bytes,
    )


if __name__ == "__main__":
    main()
