# Database Setup Guide

## Railway PostgreSQL Database

Your Telegram bot uses a **separate Railway PostgreSQL database** (not connected to your main app).

### ✅ Database Already Created

Your Railway PostgreSQL credentials:

```
Host: your_railway_host:port
Database: railway
User: postgres
Password: your_railway_db_password
```

Connection string:

```
postgresql://postgres:your_password@your_host:port/railway
```

This is **already configured** in `sample.env` ✅

---

## Setup Steps

### 1. Run Migrations

This creates the bot tables in your Railway database:

```bash
# Make sure you have the .env file (or Railway env vars set)
alembic upgrade head
```

**What this creates:**

- `users` - Telegram users
- `personas` - AI girl personalities (preset + custom)
- `chats` - Chat sessions between users and personas
- `messages` - Conversation history
- `image_jobs` - Image generation jobs

### 2. Seed Preset Personas

This adds the 4 preset AI girls to your database:

```bash
python seed_db.py
```

**Output:**

```
🌱 Starting database seeding...

📝 Creating 4 preset personas...
  ✓ Created: Mia (sweet_girlfriend)
  ✓ Created: Rei (tsundere)
  ✓ Created: Scarlett (seductive)
  ✓ Created: Luna (shy_romantic)

✅ Successfully seeded 4 preset personas!

Personas available:
  - Mia (sweet_girlfriend)
  - Rei (tsundere)
  - Scarlett (seductive)
  - Luna (shy_romantic)

🎉 Database seeding complete!
```

**Note:** The script is idempotent - if personas already exist, it will skip seeding.

---

## Verify Setup

### Check Database Connection

```bash
python -c "from app.db.base import engine; engine.connect(); print('✅ Database connected!')"
```

### Check Tables Created

```bash
# Using psql
psql postgresql://postgres:your_password@your_host:port/railway -c "\dt"
```

You should see:

```
 Schema |       Name        | Type  | Owner
--------+-------------------+-------+----------
 public | alembic_version   | table | postgres
 public | chats             | table | postgres
 public | image_jobs        | table | postgres
 public | messages          | table | postgres
 public | personas          | table | postgres
 public | users             | table | postgres
```

### Check Personas Seeded

```bash
python scripts/manage.py list-personas
```

Should show:

```
📚 Preset Personas:
  - Mia (sweet_girlfriend)
  - Rei (tsundere)
  - Scarlett (seductive)
  - Luna (shy_romantic)

Total: 4
```

---

## Database Schema

### `users`

```sql
CREATE TABLE users (
    id BIGINT PRIMARY KEY,           -- Telegram user ID
    username VARCHAR(255),
    first_name VARCHAR(255),
    locale VARCHAR(10),
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    settings JSONB
);
```

### `personas`

```sql
CREATE TABLE personas (
    id UUID PRIMARY KEY,
    owner_user_id BIGINT,            -- NULL for presets
    key VARCHAR(100) UNIQUE,         -- e.g. "sweet_girlfriend"
    name VARCHAR(255) NOT NULL,
    system_prompt TEXT NOT NULL,
    style JSONB,                     -- {"temperature": 0.8, "max_tokens": 400}
    negatives TEXT,                  -- Image negative prompts
    appearance JSONB,                -- Physical appearance for images
    is_preset BOOLEAN,
    created_at TIMESTAMP
);
```

### `chats`

```sql
CREATE TABLE chats (
    id UUID PRIMARY KEY,
    tg_chat_id BIGINT NOT NULL,     -- Telegram chat ID
    user_id BIGINT REFERENCES users(id),
    persona_id UUID REFERENCES personas(id),
    mode VARCHAR(20),                -- 'dm' or 'group'
    settings JSONB,
    state_snapshot JSONB,            -- Current conversation state
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### `messages`

```sql
CREATE TABLE messages (
    id UUID PRIMARY KEY,
    chat_id UUID REFERENCES chats(id) ON DELETE CASCADE,
    role VARCHAR(20),                -- 'user' or 'assistant'
    text TEXT,
    media JSONB,                     -- Attached media
    created_at TIMESTAMP
);
```

### `image_jobs`

```sql
CREATE TABLE image_jobs (
    id UUID PRIMARY KEY,
    chat_id UUID REFERENCES chats(id),
    persona_id UUID REFERENCES personas(id),
    user_id BIGINT REFERENCES users(id),
    prompt TEXT NOT NULL,
    negative_prompt TEXT,
    status VARCHAR(20),              -- 'queued', 'running', 'completed', 'failed'
    result_url TEXT,
    result_file_id VARCHAR(255),     -- Telegram file_id for caching
    error TEXT,
    ext JSONB,                       -- Extra metadata
    created_at TIMESTAMP,
    finished_at TIMESTAMP
);
```

---

## Database Migrations

### Check Current Migration

```bash
alembic current
```

### Show Migration History

```bash
alembic history
```

### Create New Migration

```bash
alembic revision -m "description of changes"
```

### Apply All Pending Migrations

```bash
alembic upgrade head
```

### Rollback Last Migration

```bash
alembic downgrade -1
```

---

## Production Setup (Railway)

When deploying to Railway:

1. **Database service already exists** ✅
2. **Environment variables auto-injected** by Railway:

   - `DATABASE_URL` (internal)
   - `DATABASE_PUBLIC_URL` (external)
   - `PGUSER`, `PGPASSWORD`, `PGDATABASE`, etc.

3. **Migrations run automatically** on deploy (via `Dockerfile` CMD):

   ```dockerfile
   CMD alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}
   ```

4. **Seed personas manually** after first deploy:
   ```bash
   railway run python seed_db.py
   ```

---

## Troubleshooting

### "relation does not exist"

**Solution:** Run migrations

```bash
alembic upgrade head
```

### "password authentication failed"

**Solution:** Check DATABASE_URL in `.env` or Railway env vars

### "database does not exist"

**Solution:** Railway should auto-create the `railway` database. If not, check your Railway PostgreSQL service.

### "SSL required"

**Solution:** Railway PostgreSQL doesn't require SSL for internal connections. If using external connection, add `?sslmode=require`:

```
postgresql://postgres:pass@host:port/railway?sslmode=require
```

### "No personas in database"

**Solution:** Run seed script

```bash
python seed_db.py
```

---

## Database Management

### Connect to Database

**Using psql:**

```bash
psql postgresql://postgres:your_password@your_host:port/railway
```

**Using Railway CLI:**

```bash
railway run psql $DATABASE_URL
```

### Query Examples

**Count users:**

```sql
SELECT COUNT(*) FROM users;
```

**List all personas:**

```sql
SELECT name, key, is_preset FROM personas;
```

**Recent conversations:**

```sql
SELECT u.username, p.name, c.created_at
FROM chats c
JOIN users u ON c.user_id = u.id
JOIN personas p ON c.persona_id = p.id
ORDER BY c.created_at DESC
LIMIT 10;
```

**Image generation stats:**

```sql
SELECT status, COUNT(*)
FROM image_jobs
GROUP BY status;
```

---

## Backup & Restore

### Backup Database

```bash
pg_dump postgresql://postgres:your_password@your_host:port/railway > backup.sql
```

### Restore Database

```bash
psql postgresql://postgres:your_password@your_host:port/railway < backup.sql
```

**Note:** Railway provides automatic backups for your database.

---

## ✅ You're Done!

Your Railway PostgreSQL database is ready:

- ✅ Credentials configured
- ✅ Connection string in `sample.env`
- ✅ Tables will be created by `alembic upgrade head`
- ✅ Personas will be seeded by `python seed_db.py`

Just run the two commands and your database is fully set up! 🚀
