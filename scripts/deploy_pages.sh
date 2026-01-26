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

if [[ -z "${CF_PAGES_PROJECT_MINIAPP:-}" ]]; then
  echo "CF_PAGES_PROJECT_MINIAPP is required"
  exit 1
fi

if [[ -z "${CF_PAGES_PROJECT_ANALYTICS:-}" ]]; then
  echo "CF_PAGES_PROJECT_ANALYTICS is required"
  exit 1
fi

if [[ -z "${VITE_API_BASE_URL:-}" ]]; then
  echo "VITE_API_BASE_URL is required (e.g., https://your-api.up.railway.app)"
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_BASE_URL="${VITE_API_BASE_URL}"

echo "▶ Deploying Mini App to Cloudflare Pages"
pushd "${ROOT_DIR}/miniapp" >/dev/null
npm ci
VITE_API_BASE_URL="${API_BASE_URL}" npm run build
CLOUDFLARE_ACCOUNT_ID="${CLOUDFLARE_ACCOUNT_ID}" \
  npx wrangler pages deploy dist \
    --project-name "${CF_PAGES_PROJECT_MINIAPP}" \
    --branch "production"
popd >/dev/null

echo "▶ Deploying Analytics Dashboard to Cloudflare Pages"
pushd "${ROOT_DIR}/analytics-dashboard" >/dev/null
npm ci
VITE_API_BASE_URL="${API_BASE_URL}" npm run build
CLOUDFLARE_ACCOUNT_ID="${CLOUDFLARE_ACCOUNT_ID}" \
  npx wrangler pages deploy dist \
    --project-name "${CF_PAGES_PROJECT_ANALYTICS}" \
    --branch "production"
popd >/dev/null

echo "✅ Pages deploy complete"
