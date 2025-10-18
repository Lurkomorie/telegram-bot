# Schema Synchronization Between Projects

Now that you're creating a separate admin project, here are the best ways to keep database schemas synchronized:

## Option 1: Shared Models Package (Recommended ⭐)

Create a shared Python package that both projects import.

### Structure:

```
telegram-bot-shared/
├── setup.py
├── telegram_bot_models/
│   ├── __init__.py
│   └── models.py      # Your SQLAlchemy models
│
telegram-bot/          # Main bot project
├── requirements.txt   # Add: telegram-bot-shared
├── app/
│   └── db/
│       └── models.py  # Import from shared package
│
telegram-bot-admin/    # Admin project
├── requirements.txt   # Add: telegram-bot-shared
└── models.py          # Import from shared package
```

### Implementation:

**1. Create shared package:**

```bash
mkdir telegram-bot-shared
cd telegram-bot-shared
```

**telegram-bot-shared/setup.py:**

```python
from setuptools import setup, find_packages

setup(
    name="telegram-bot-models",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "sqlalchemy==2.0.25",
    ],
)
```

**2. Move models to shared package:**

```bash
# Copy your current models.py to shared package
cp ../telegram-bot/app/db/models.py telegram_bot_models/models.py
```

**3. Install in both projects:**

```bash
# In main bot project
pip install -e ../telegram-bot-shared

# In admin project
pip install -e ../telegram-bot-shared
```

**4. Update imports:**

```python
# Instead of: from app.db.models import User, Persona
# Use: from telegram_bot_models.models import User, Persona
```

**Pros:**

- ✅ Single source of truth
- ✅ Type safety and IDE completion
- ✅ Migrations stay in sync
- ✅ Easy to version control

**Cons:**

- ⚠️ Need to maintain separate package
- ⚠️ Both projects must update when models change

---

## Option 2: Direct Database Connection (Simplest)

Admin project connects directly to the same database.

### Structure:

```
telegram-bot/          # Main project with models
├── app/db/models.py   # Source of truth
└── alembic/           # Migrations

telegram-bot-admin/    # Admin project
├── models.py          # Copy of models (manual sync)
└── No migrations      # Uses schema from main project
```

### Implementation:

**1. Admin project setup:**

```python
# admin/models.py - Copy from main project
from sqlalchemy import Column, Integer, String, DateTime
# ... copy all your models

# admin/main.py
from sqladmin import Admin, ModelView
from models import User, Persona  # Use copied models

admin = Admin(app, engine)
```

**2. Keep synced manually:**

- When you change schema in main project, copy models to admin
- Run migrations ONLY in main project
- Admin just reads from the same database

**Pros:**

- ✅ Very simple setup
- ✅ Admin is read-only (safer)
- ✅ No package management

**Cons:**

- ⚠️ Manual copying required
- ⚠️ Easy to get out of sync
- ⚠️ No compile-time checks

---

## Option 3: API-Based Admin (Most Secure)

Main bot exposes REST API endpoints, admin calls them.

### Structure:

```
telegram-bot/          # Main project
├── app/api/           # NEW: REST API endpoints
│   ├── users.py       # GET/POST/PUT/DELETE /api/users
│   ├── personas.py    # GET/POST/PUT/DELETE /api/personas
│   └── auth.py        # API authentication
└── No direct DB access from admin

telegram-bot-admin/    # Admin frontend
├── react-admin/       # Or any admin UI framework
└── Calls API          # No database connection
```

### Implementation:

**1. Add API to main project:**

```python
# app/api/users.py
from fastapi import APIRouter, Depends
from app.db import crud
from app.db.base import get_db

router = APIRouter(prefix="/api")

@router.get("/users")
def list_users(db: Session = Depends(get_db)):
    return crud.get_users(db)

@router.post("/users")
def create_user(user_data: UserCreate, db: Session = Depends(get_db)):
    return crud.create_user(db, user_data)
```

**2. Admin project uses API client:**

```python
# admin/services/api_client.py
import httpx

class BotAPIClient:
    def __init__(self, base_url, api_key):
        self.base_url = base_url
        self.api_key = api_key

    def get_users(self):
        response = httpx.get(f"{self.base_url}/api/users",
                            headers={"Authorization": f"Bearer {self.api_key}"})
        return response.json()
```

**Pros:**

- ✅ Complete separation
- ✅ Most secure (no direct DB access)
- ✅ Can version API independently
- ✅ Admin can be any framework (React, Vue, etc.)
- ✅ Natural schema sync through API contract

**Cons:**

- ⚠️ More development work
- ⚠️ API overhead
- ⚠️ Need API versioning

---

## Option 4: Git Submodule for Models

Use Git submodules to share model files.

### Structure:

```
telegram-bot-models/   # Separate git repo
└── models.py

telegram-bot/
└── app/db/models/     # Git submodule pointing to above
    └── models.py      # Actually in telegram-bot-models repo

telegram-bot-admin/
└── models/            # Git submodule pointing to above
    └── models.py      # Same file as main project
```

### Implementation:

```bash
# Create models repo
git init telegram-bot-models
# Move models.py there

# Add as submodule in main project
cd telegram-bot
git submodule add ../telegram-bot-models app/db/models

# Add as submodule in admin project
cd telegram-bot-admin
git submodule add ../telegram-bot-models models

# Update both projects when models change
git submodule update --remote
```

**Pros:**

- ✅ Version controlled
- ✅ Single source of truth
- ✅ Git tracks changes

**Cons:**

- ⚠️ Git submodules can be tricky
- ⚠️ Need to remember to update submodules
- ⚠️ Not ideal for frequent changes

---

## My Recommendation

For your use case, I recommend **Option 1 (Shared Package)** or **Option 2 (Direct Connection)**:

### Choose Option 1 (Shared Package) if:

- ✅ You want proper dependency management
- ✅ You plan to have multiple services/projects
- ✅ You want type safety across projects
- ✅ You're comfortable with Python packaging

### Choose Option 2 (Direct Connection) if:

- ✅ You want the simplest solution
- ✅ Admin is mostly read-only
- ✅ Schema changes are infrequent
- ✅ You're okay manually copying files

### Quick Start: Option 2 (Simplest)

1. **In your admin project:**

```bash
# Copy models from main project
cp ../telegram-bot/app/db/models.py ./models.py

# Use same DATABASE_URL environment variable
DATABASE_URL=postgresql://...  # Same as main project
```

2. **Create admin app:**

```python
# admin/main.py
from sqladmin import Admin, ModelView
from models import User, Persona, PersonaHistoryStart, Chat, Message, ImageJob
from sqlalchemy import create_engine

engine = create_engine(DATABASE_URL)
admin = Admin(app, engine)

# Register views...
```

3. **When schema changes:**

```bash
# In main project: make model changes and run migration
alembic revision --autogenerate -m "add new field"
alembic upgrade head

# In admin project: just copy the new models.py
cp ../telegram-bot/app/db/models.py ./models.py
# Restart admin server
```

That's it! The admin connects to the same database, so schema is always in sync at runtime.

---

## Important Notes

- **Migrations:** Only run migrations from ONE project (the main bot)
- **Database:** Both projects connect to the SAME database
- **Environment:** Use same `DATABASE_URL` in both projects
- **Security:** Admin should have limited/read-only DB permissions if possible

Need help setting up any of these options? Let me know which one you prefer!

