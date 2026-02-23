# Infrastructure Rollout Runbook

## Scope

This runbook covers deployment-side steps for:

- Mini App canonical host switch to Vercel with backup host strategy.
- Postgres volume recovery via blob purge + sanitized cutover.

Code-side changes are already in place for:

- file_id-first image cache reuse,
- blur/unlock via Telegram file_id pointers (no DB blob),
- analytics retention cleanup,
- error-only logging mode.

## A. Mini App Canonical Host (Vercel) + Backup Host

1. Deploy Mini App from:
   - `/Users/artemtrifanuk/Documents/telegram-bot/miniapp`
2. Configure production env vars:
   - `MINIAPP_BASE_URL=https://<primary-vercel-domain>`
   - `MINIAPP_BACKUP_BASE_URL=https://<backup-domain>` (optional, Netlify or second Vercel project)
   - `MINIAPP_ACTIVE_HOST=primary` (switch to `backup` if regional blocking appears)
3. Configure backend CORS:
   - Either set `CORS_ALLOW_ORIGINS` explicitly,
   - Or rely on automatic origin merge from `MINIAPP_BASE_URL` and `MINIAPP_BACKUP_BASE_URL`.
4. Keep Railway `/miniapp` paths as redirects:
   - already implemented when `SERVE_LOCAL_STATIC=false`.
5. Verify diagnostics:
   - `GET /api/miniapp/diagnostics/auth`
   - Confirm `auth_required`, `auth_valid`, and `cors_allow_origins`.
6. Verify fallback switching (no code change):
   - flip `MINIAPP_ACTIVE_HOST=backup` and redeploy.

## B. Postgres Volume Recovery

### 1) Immediate purge on current DB (safe, batched)

Dry-run first:

```bash
python scripts/purge_image_job_blobs.py --batch-size 1000 --max-rows 50000
```

Execute:

```bash
python scripts/purge_image_job_blobs.py --execute --batch-size 1000
```

What it removes:

- `image_jobs.ext.blurred_original_data`
- oversized blob-like JSON values in `image_jobs.ext`

### 2) Vacuum/reclaim expectations

- Purge reduces logical table size immediately.
- Physical reclaim for TOAST-heavy tables usually requires:
  - autovacuum over time, or
  - explicit maintenance window with `VACUUM (FULL)` / table rewrite, or
  - DB cutover to fresh instance.

### 3) Sanitized DB cutover (recommended for guaranteed reclaim)

1. Create new Railway Postgres instance.
2. Put app in short maintenance mode (2-5 minutes target).
3. Copy schema/migrations to new DB.
4. Copy data table-by-table from old DB to new DB:
   - include all product data and active chats.
   - for `tg_analytics_events`, keep only recent retention window (30 days).
5. Run sanity checks:
   - row counts for critical tables,
   - sample reads for chats/image_jobs/purchases,
   - image callback + unlock flow smoke test.
6. Switch `DATABASE_URL` to new DB and deploy.
7. Keep old DB read-only for rollback window (24-72h).
8. If stable, remove old DB.

## C. New Runtime Flags

- `MEDIA_CACHE_CHAT_ID` (required for blur/unlock flow)
- `ANALYTICS_RETENTION_DAYS` (default `30`)
- `BLUR_ORIGINAL_RETENTION_HOURS` (default `48`)
- `ERROR_ONLY_LOGS` (default `true`)
- `ENABLE_MINIAPP_AUTH_DIAGNOSTICS` (default `true`)
- `MINIAPP_BACKUP_BASE_URL`
- `MINIAPP_ACTIVE_HOST` (`primary` or `backup`)

## D. Post-Deploy Verification Checklist

1. Generate image from chat:
   - ensure first response is immediate.
   - confirm `result_file_id` is written on completed job.
2. Regenerate same prompt:
   - cache should serve via `file_id` first.
3. Blur/unlock flow:
   - blurred image appears with unlock button,
   - unlock sends original using `blurred_original_file_id`,
   - no `blurred_original_data` stored in DB.
4. Scheduler checks (after next daily cycle):
   - analytics retention deletion runs,
   - blurred pointer cleanup runs.
