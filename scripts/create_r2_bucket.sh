#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${CLOUDFLARE_ACCOUNT_ID:-}" ]]; then
  echo "CLOUDFLARE_ACCOUNT_ID is required"
  exit 1
fi

if [[ -z "${CLOUDFLARE_API_TOKEN:-}" ]]; then
  echo "CLOUDFLARE_API_TOKEN is required"
  exit 1
fi

if [[ -z "${R2_BUCKET_NAME:-}" ]]; then
  echo "R2_BUCKET_NAME is required"
  exit 1
fi

CLOUDFLARE_ACCOUNT_ID="${CLOUDFLARE_ACCOUNT_ID}" \
  npx wrangler r2 bucket create "${R2_BUCKET_NAME}"
echo "✅ R2 bucket ready: ${R2_BUCKET_NAME}"
