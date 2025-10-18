# Telegram Bot Admin Panel - Implementation Plan

## Project Overview

Build a **standalone admin panel** to manage a Telegram bot's PostgreSQL database. This admin panel is a separate Railway project that connects to the same database as the main Telegram bot.

### ✅ Already Completed

- [x] Created `telegram-bot-admin` folder
- [x] Created `.env` file with configuration
- [x] Copied `models.py` from main bot

### What This Admin Panel Manages

1. **Users** - Telegram bot users
2. **Personas** - AI character profiles (public and custom)
3. **Persona Greetings** - Initial greeting messages for personas
4. **Chats** - Conversation sessions between users and personas
5. **Messages** - Chat message history
6. **Image Jobs** - AI image generation tasks

### Key Requirements

- **Authentication** required (username/password)
- **Modern UI** with search, filters, pagination
- **Relationship handling** - properly display foreign keys
- **Bulk operations** - select and delete multiple records
- **Export functionality** - CSV/JSON export
- **Railway deployment** - same network as main bot

---

## Technology Stack

```
FastAPI        - Web framework
SQLAdmin       - Admin interface (built for FastAPI + SQLAlchemy)
SQLAlchemy     - ORM (matches main project)
PostgreSQL     - Database (same as main bot via Railway internal network)
Uvicorn        - ASGI server
Railway        - Deployment platform
```

---

## Current Environment Configuration

Your `.env` file is already configured:

```bash
DATABASE_URL="postgresql://postgres:XGlKgqmSQtgFMVsVkGtFjAzYZlAULdwo@postgres.railway.internal:5432/railway"
ENV="production"
LOG_LEVEL="INFO"
ADMIN_USERNAME="admin"
ADMIN_PASSWORD="Lurkomorie123"
ADMIN_SECRET_KEY="X5g4T0miZbKJYMZPpB3ctbIuvXkvT7wA"
```

**Important Notes:**

- ✅ Using Railway internal network (`postgres.railway.internal`) - faster and more secure
- ✅ `ADMIN_SECRET_KEY` is properly set (32 characters)
- ⚠️ **Security:** Change `ADMIN_PASSWORD` before sharing this document
- ✅ Both main bot and admin panel share the same database

---

## Project Structure

Your `telegram-bot-admin` folder should have this structure:

```
telegram-bot-admin/
├── .env                    # ✅ Already created
├── models.py               # ✅ Already copied from main bot
├── requirements.txt        # Need to create
├── main.py                 # Need to create
├── auth.py                 # Need to create
├── views.py                # Need to create
├── Procfile                # Need to create (for Railway)
└── README.md               # Optional
```

---

## Step-by-Step Implementation

### Step 1: Create requirements.txt

Create `requirements.txt` in the `telegram-bot-admin` folder:

```txt
fastapi==0.109.0
uvicorn[standard]==0.27.0
sqladmin==0.18.0
sqlalchemy==2.0.25
psycopg2-binary==2.9.9
python-dotenv==1.0.0
itsdangerous==2.1.2
```

### Step 2: Create Authentication Module

Create `auth.py`:

```python
"""
Admin authentication
"""
import os
import secrets
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from dotenv import load_dotenv

load_dotenv()


class AdminAuth(AuthenticationBackend):
    """Basic HTTP authentication for admin panel"""

    async def login(self, request: Request) -> bool:
        """Handle login"""
        form = await request.form()
        username = form.get("username")
        password = form.get("password")

        # Get credentials from environment
        admin_username = os.getenv("ADMIN_USERNAME", "admin")
        admin_password = os.getenv("ADMIN_PASSWORD")

        if not admin_password:
            raise ValueError("ADMIN_PASSWORD not set in environment")

        # Constant-time comparison
        username_valid = secrets.compare_digest(username, admin_username)
        password_valid = secrets.compare_digest(password, admin_password)

        if username_valid and password_valid:
            request.session.update({"authenticated": True})
            return True

        return False

    async def logout(self, request: Request) -> bool:
        """Handle logout"""
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        """Check authentication status"""
        return request.session.get("authenticated", False)
```

### Step 3: Create Admin Views

Create `views.py`:

```python
"""
Admin panel views for all models
"""
from sqladmin import ModelView
from wtforms import TextAreaField
from models import User, Persona, PersonaHistoryStart, Chat, Message, ImageJob


class UserAdmin(ModelView, model=User):
    """Manage Users"""
    name = "User"
    name_plural = "Users"
    icon = "fa-solid fa-user"

    column_list = [User.id, User.username, User.first_name, User.locale, User.created_at]
    column_searchable_list = [User.username, User.first_name]
    column_sortable_list = [User.id, User.username, User.created_at]
    column_default_sort = [(User.created_at, True)]
    column_details_exclude_list = [User.settings]
    form_excluded_columns = [User.chats, User.personas, User.settings]

    can_create = False  # Read-only recommended
    can_edit = True
    can_delete = False  # Dangerous - keep disabled
    can_export = True
    page_size = 50


class PersonaAdmin(ModelView, model=Persona):
    """Manage Personas"""
    name = "Persona"
    name_plural = "Personas"
    icon = "fa-solid fa-robot"

    column_list = [Persona.id, Persona.name, Persona.key, Persona.visibility, Persona.created_at]
    column_searchable_list = [Persona.name, Persona.key, Persona.description]
    column_sortable_list = [Persona.name, Persona.visibility, Persona.created_at]
    column_default_sort = [(Persona.created_at, True)]
    column_filters = [Persona.visibility]

    form_excluded_columns = [Persona.chats, Persona.history_starts]
    form_overrides = {
        "prompt": TextAreaField,
        "description": TextAreaField,
        "intro": TextAreaField,
    }

    can_create = True
    can_edit = True
    can_delete = True
    can_export = True
    page_size = 50


class PersonaHistoryStartAdmin(ModelView, model=PersonaHistoryStart):
    """Manage Persona Greetings"""
    name = "Persona Greeting"
    name_plural = "Persona Greetings"
    icon = "fa-solid fa-comment"

    column_list = [PersonaHistoryStart.id, PersonaHistoryStart.persona, PersonaHistoryStart.text, PersonaHistoryStart.created_at]
    column_searchable_list = [PersonaHistoryStart.text]
    column_default_sort = [(PersonaHistoryStart.created_at, True)]

    form_overrides = {"text": TextAreaField}
    form_ajax_refs = {
        "persona": {
            "fields": ("name", "key"),
            "order_by": "name",
        }
    }

    can_create = True
    can_edit = True
    can_delete = True
    can_export = True
    page_size = 50


class ChatAdmin(ModelView, model=Chat):
    """Manage Chats"""
    name = "Chat"
    name_plural = "Chats"
    icon = "fa-solid fa-comments"

    column_list = [Chat.id, Chat.tg_chat_id, Chat.user, Chat.persona, Chat.mode, Chat.updated_at]
    column_searchable_list = [Chat.tg_chat_id]
    column_default_sort = [(Chat.updated_at, True)]
    column_filters = [Chat.mode]
    column_details_exclude_list = [Chat.state_snapshot, Chat.settings]

    form_excluded_columns = [Chat.messages]
    form_ajax_refs = {
        "user": {"fields": ("username", "first_name"), "order_by": "id"},
        "persona": {"fields": ("name", "key"), "order_by": "name"}
    }

    can_create = False
    can_edit = True
    can_delete = True  # Careful - will cascade delete messages
    can_export = True
    page_size = 50


class MessageAdmin(ModelView, model=Message):
    """Manage Messages"""
    name = "Message"
    name_plural = "Messages"
    icon = "fa-solid fa-message"

    column_list = [Message.id, Message.chat, Message.role, Message.text, Message.created_at]
    column_searchable_list = [Message.text]
    column_default_sort = [(Message.created_at, True)]
    column_filters = [Message.role, Message.is_processed]
    column_details_exclude_list = [Message.media, Message.state_snapshot]

    form_overrides = {"text": TextAreaField}
    form_ajax_refs = {
        "chat": {"fields": ("tg_chat_id",), "order_by": "created_at"}
    }

    can_create = False
    can_edit = False  # Messages shouldn't be edited
    can_delete = True
    can_export = True
    page_size = 100


class ImageJobAdmin(ModelView, model=ImageJob):
    """Manage Image Jobs"""
    name = "Image Job"
    name_plural = "Image Jobs"
    icon = "fa-solid fa-image"

    column_list = [ImageJob.id, ImageJob.persona, ImageJob.status, ImageJob.created_at]
    column_searchable_list = [ImageJob.prompt]
    column_default_sort = [(ImageJob.created_at, True)]
    column_filters = [ImageJob.status]
    column_details_exclude_list = [ImageJob.ext]

    form_overrides = {
        "prompt": TextAreaField,
        "negative_prompt": TextAreaField,
    }
    form_ajax_refs = {
        "persona": {"fields": ("name", "key"), "order_by": "name"}
    }

    can_create = False
    can_edit = True
    can_delete = True
    can_export = True
    page_size = 50
```

### Step 4: Create Main Application

Create `main.py`:

```python
"""
Telegram Bot Admin Panel
"""
import os
from dotenv import load_dotenv
from fastapi import FastAPI
from sqlalchemy import create_engine
from sqladmin import Admin
from starlette.middleware.sessions import SessionMiddleware

# Load environment variables
load_dotenv()

# Import authentication and views
from auth import AdminAuth
from views import (
    UserAdmin,
    PersonaAdmin,
    PersonaHistoryStartAdmin,
    ChatAdmin,
    MessageAdmin,
    ImageJobAdmin
)

# Get configuration from environment
DATABASE_URL = os.getenv("DATABASE_URL")
ADMIN_SECRET_KEY = os.getenv("ADMIN_SECRET_KEY")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL not set in environment")
if not ADMIN_SECRET_KEY:
    raise ValueError("ADMIN_SECRET_KEY not set in environment")

# Create FastAPI app
app = FastAPI(
    title="Telegram Bot Admin Panel",
    description="Admin interface for Telegram Bot database management",
    version="1.0.0"
)

# Add session middleware for authentication
app.add_middleware(
    SessionMiddleware,
    secret_key=ADMIN_SECRET_KEY,
    session_cookie="admin_session",
    max_age=3600  # 1 hour
)

# Create database engine
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

# Initialize SQLAdmin
authentication_backend = AdminAuth(secret_key=ADMIN_SECRET_KEY)
admin = Admin(
    app=app,
    engine=engine,
    authentication_backend=authentication_backend,
    title="Telegram Bot Admin"
)

# Register all model views
admin.add_view(UserAdmin)
admin.add_view(PersonaAdmin)
admin.add_view(PersonaHistoryStartAdmin)
admin.add_view(ChatAdmin)
admin.add_view(MessageAdmin)
admin.add_view(ImageJobAdmin)

print("✅ Admin panel initialized")


# Health check endpoint
@app.get("/")
def root():
    return {
        "status": "ok",
        "admin_url": "/admin",
        "message": "Navigate to /admin to access the admin panel"
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
```

### Step 5: Create Procfile for Railway

Create `Procfile`:

```
web: uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
```

### Step 6: Create README (Optional)

Create `README.md`:

```markdown
# Telegram Bot Admin Panel

Admin interface for managing the Telegram Bot database.

## Features

- User management
- Persona management (AI characters)
- Chat session monitoring
- Message history viewing
- Image generation job tracking

## Access

- **URL:** `/admin`
- **Login:** Use ADMIN_USERNAME and ADMIN_PASSWORD from environment

## Technology

- FastAPI + SQLAdmin
- PostgreSQL (shared with main bot)
- Deployed on Railway
```

---

## Railway Deployment

### Step 1: Initialize Git Repository

```bash
cd telegram-bot-admin
git init
git add .
git commit -m "Initial admin panel setup"
```

### Step 2: Create Railway Project

1. Go to [Railway](https://railway.app)
2. Click **"New Project"**
3. Select **"Deploy from GitHub repo"** (or "Empty Project")

### Step 3: Connect to Same Database

**Important:** Your admin panel needs to use the **same database** as your main bot.

**Option A: Reference Existing Database (Recommended)**

1. In Railway dashboard, click **"New"** → **"Database"** → **"Add PostgreSQL"**
2. **DON'T create a new database!**
3. Instead, go to your main bot's PostgreSQL service
4. Click **"Connect"** → Copy the **Private URL**
5. In your admin panel service, add environment variable:
   ```
   DATABASE_URL = <private-url-from-main-bot-postgres>
   ```

**Option B: Use Internal Network (Your Current Setup)**

Your `.env` already has:

```
DATABASE_URL="postgresql://postgres:XGlKgqmSQtgFMVsVkGtFjAzYZlAULdwo@postgres.railway.internal:5432/railway"
```

This works if:

- Admin panel and main bot are in the **same Railway project**
- They share the same **private network**

### Step 4: Add Environment Variables in Railway

In Railway dashboard, add these environment variables to your admin panel service:

```bash
DATABASE_URL=postgresql://postgres:XGlKgqmSQtgFMVsVkGtFjAzYZlAULdwo@postgres.railway.internal:5432/railway
ENV=production
LOG_LEVEL=INFO
ADMIN_USERNAME=admin
ADMIN_PASSWORD=Lurkomorie123
ADMIN_SECRET_KEY=X5g4T0miZbKJYMZPpB3ctbIuvXkvT7wA
```

**⚠️ Security Note:** Change `ADMIN_PASSWORD` to something more secure before deploying!

### Step 5: Deploy

Railway will automatically:

1. Detect it's a Python project
2. Install dependencies from `requirements.txt`
3. Run the command from `Procfile`
4. Assign a public URL

### Step 6: Access Your Admin Panel

Once deployed, Railway will give you a URL like:

```
https://telegram-bot-admin-production-xxxx.up.railway.app
```

Navigate to:

```
https://telegram-bot-admin-production-xxxx.up.railway.app/admin
```

Login with:

- **Username:** `admin`
- **Password:** `Lurkomorie123` (or your updated password)

---

## Railway Configuration Tips

### Recommended Railway Setup

**Option 1: Separate Projects** (More Isolated)

```
Railway Project 1: telegram-bot (main bot)
├── PostgreSQL Service
└── Bot Service

Railway Project 2: telegram-bot-admin
└── Admin Service (connects to Project 1's database)
```

**Option 2: Same Project** (Simpler, Your Current Setup)

```
Railway Project: telegram-bot
├── PostgreSQL Service
├── Bot Service
└── Admin Service (uses internal network)
```

### Private Network Configuration

If using same project, both services can use `postgres.railway.internal`:

**Main Bot:**

```
DATABASE_URL=postgresql://postgres:password@postgres.railway.internal:5432/railway
```

**Admin Panel:**

```
DATABASE_URL=postgresql://postgres:password@postgres.railway.internal:5432/railway
```

### Environment Variables

Make sure to set in Railway (not just `.env`):

- `DATABASE_URL`
- `ADMIN_USERNAME`
- `ADMIN_PASSWORD`
- `ADMIN_SECRET_KEY`
- `ENV=production`

---

## Local Development

To test locally before deploying:

```bash
cd telegram-bot-admin

# Install dependencies
pip install -r requirements.txt

# Run locally
uvicorn main:app --reload --port 8000
```

Access at: `http://localhost:8000/admin`

**Note:** For local development, you'll need to update `DATABASE_URL` in `.env` to use the **public URL** instead of `postgres.railway.internal` (internal network only works within Railway).

Get public URL from Railway:

```
DATABASE_URL=postgresql://postgres:password@postgres.railway.app:5432/railway
```

---

## Security Considerations

### ⚠️ Important Security Notes

1. **Change Default Password**

   ```bash
   ADMIN_PASSWORD=<use-a-strong-password-at-least-16-chars>
   ```

2. **Don't Expose Admin Publicly**

   - Consider adding IP whitelist in Railway
   - Use VPN for access
   - Or keep the admin URL private

3. **Read-Only Recommended**

   - Most models are set to `can_create = False`
   - Prevents accidental data creation
   - Edit-only is safer

4. **Dangerous Operations**

   - Deleting Chats will cascade delete Messages
   - Deleting Users fails if they have chats
   - Test on staging first!

5. **Database Permissions**
   - Admin panel should have limited DB permissions
   - Consider creating a separate DB user with restricted rights

---

## Testing Checklist

After deployment, verify:

- [ ] Can access Railway URL
- [ ] Login page loads at `/admin`
- [ ] Can login with credentials
- [ ] See all 6 models in sidebar (Users, Personas, Greetings, Chats, Messages, Image Jobs)
- [ ] Can view list of each model
- [ ] Search works
- [ ] Filters work (visibility, status, role)
- [ ] Sorting works
- [ ] Can view record details
- [ ] Foreign key relationships display (personas in greetings, etc.)
- [ ] Can create new Persona
- [ ] Can create new Persona Greeting with persona dropdown
- [ ] Can edit records
- [ ] Can delete records (if enabled)
- [ ] Export to CSV works
- [ ] Logout works
- [ ] Can login again

---

## Schema Synchronization

### When Main Bot Schema Changes

Your `models.py` is a copy from the main bot. When the bot's schema changes:

**1. Main bot updates schema:**

```bash
# In main bot project
cd telegram-bot
# Edit app/db/models.py
alembic revision --autogenerate -m "add new field"
alembic upgrade head
```

**2. Update admin panel:**

```bash
# Copy updated models.py
cp ../telegram-bot/app/db/models.py ./telegram-bot-admin/models.py

# Commit and push
cd telegram-bot-admin
git add models.py
git commit -m "Update models from main bot"
git push

# Railway will auto-redeploy
```

---

## Troubleshooting

### "Cannot connect to database"

**Problem:** Railway internal network not working

**Solutions:**

1. Make sure admin and bot are in **same Railway project**
2. Check `DATABASE_URL` uses `postgres.railway.internal`
3. Try using **public database URL** instead
4. Verify database service is running

### "Static files not loading / No styling"

**Problem:** SQLAdmin static files not serving

**Solutions:**

1. Check Railway logs for errors
2. SQLAdmin should serve static files automatically
3. Try clearing browser cache
4. Check if port is configured correctly in Procfile

### "Persona dropdown is empty"

**Problem:** No personas in database

**Solutions:**

1. Use main bot to create personas first
2. Or create manually in admin (if `can_create = True`)
3. Check database: `SELECT * FROM personas;`

### "Authentication not working"

**Problem:** Session middleware or credentials

**Solutions:**

1. Verify `ADMIN_SECRET_KEY` is set in Railway
2. Check `ADMIN_PASSWORD` matches what you're entering
3. Try different browser (clear cookies)
4. Check Railway logs for authentication errors

### "Railway deployment fails"

**Problem:** Missing dependencies or configuration

**Solutions:**

1. Check Railway build logs
2. Verify `requirements.txt` is complete
3. Make sure `Procfile` exists
4. Check all environment variables are set

---

## Monitoring & Logs

### View Railway Logs

```bash
# In Railway dashboard
1. Select your admin panel service
2. Click "Logs" tab
3. Filter by log level (Error, Warning, Info)
```

### Check Admin Activity

Monitor what admins are doing:

- Railway logs show all HTTP requests
- Check database query logs (if enabled)
- Consider adding audit logging to models

---

## Next Steps

After successful deployment:

1. ✅ **Test all functionality** using checklist above
2. 🔒 **Change default password** to something secure
3. 📝 **Document admin workflows** for your team
4. 🔄 **Set up schema sync process** (manual or automated)
5. 📊 **Consider adding analytics** dashboard
6. 🚨 **Set up monitoring** alerts for admin panel downtime
7. 💾 **Regular database backups** (Railway has this built-in)

---

## Support Resources

- **SQLAdmin Docs:** https://aminalaee.github.io/sqladmin/
- **FastAPI Docs:** https://fastapi.tiangolo.com/
- **Railway Docs:** https://docs.railway.app/
- **SQLAlchemy Docs:** https://docs.sqlalchemy.org/

---

## Summary

Your admin panel setup is straightforward:

1. ✅ **Already done:** Created folder, env, copied models
2. 📝 **Next:** Create `requirements.txt`, `auth.py`, `views.py`, `main.py`, `Procfile`
3. 🚀 **Deploy:** Push to Railway, set environment variables
4. 🔐 **Access:** `https://your-app.railway.app/admin`

**Key Points:**

- ✅ Same database as main bot (via Railway internal network)
- ✅ Separate Railway service (isolated deployment)
- ✅ SQLAdmin handles all UI automatically
- ✅ Authentication protects access
- ✅ Read-mostly mode prevents accidents

The admin panel will share your bot's database but run as a completely separate service on Railway. When your bot's schema changes, just copy the updated `models.py` file and Railway will auto-redeploy.

Good luck with your deployment! 🚀
