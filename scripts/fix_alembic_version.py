#!/usr/bin/env python3
"""
Pre-migration script to fix alembic_version issues.

This script checks if the alembic_version table references a migration
that doesn't exist, and fixes it by setting it to the latest valid revision.

Usage:
    python scripts/fix_alembic_version.py
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.base import engine
from sqlalchemy import text
from glob import glob
import re

def get_existing_revisions():
    """Get all revision IDs from migration files"""
    migrations_dir = Path(__file__).parent.parent / "app" / "db" / "migrations" / "versions"
    revisions = []
    
    for migration_file in sorted(migrations_dir.glob("*.py")):
        if migration_file.name.startswith("__"):
            continue
        
        with open(migration_file, 'r') as f:
            content = f.read()
            # Extract revision = 'XXX'
            match = re.search(r"^revision\s*=\s*['\"]([^'\"]+)['\"]", content, re.MULTILINE)
            if match:
                revisions.append(match.group(1))
    
    return revisions

def get_latest_revision():
    """Get the latest (highest numbered) revision"""
    revisions = get_existing_revisions()
    if not revisions:
        return None
    
    # Sort to get the latest one
    # Assuming format like '001', '002', ..., '021'
    return sorted(revisions, key=lambda x: int(x) if x.isdigit() else x)[-1]

def check_and_fix_alembic_version():
    """Check alembic_version and fix if invalid"""
    print("🔍 Checking alembic_version...")
    
    existing_revisions = get_existing_revisions()
    latest_revision = get_latest_revision()
    
    if not latest_revision:
        print("❌ No migration files found!")
        return False
    
    print(f"📋 Found {len(existing_revisions)} migration files")
    print(f"✨ Latest revision: {latest_revision}")
    
    try:
        with engine.connect() as conn:
            # Check if alembic_version table exists
            result = conn.execute(text(
                "SELECT EXISTS (SELECT FROM information_schema.tables "
                "WHERE table_name = 'alembic_version')"
            ))
            table_exists = result.scalar()
            
            if not table_exists:
                print("ℹ️  alembic_version table doesn't exist yet (fresh database)")
                return True
            
            # Get current version
            result = conn.execute(text('SELECT version_num FROM alembic_version'))
            current_version = result.fetchone()
            
            if not current_version:
                print("ℹ️  No version in alembic_version table")
                return True
            
            current = current_version[0]
            print(f"📍 Current DB version: {current}")
            
            # Check if current version exists in migrations
            if current in existing_revisions:
                print(f"✅ Current version '{current}' is valid")
                return True
            
            # Invalid version - needs fixing
            print(f"❌ Current version '{current}' not found in migration files!")
            print(f"🔧 Fixing: Setting version to '{latest_revision}'")
            
            # Fix the version
            conn.execute(text('DELETE FROM alembic_version'))
            conn.execute(text(f"INSERT INTO alembic_version (version_num) VALUES ('{latest_revision}')"))
            conn.commit()
            
            # Verify fix
            result = conn.execute(text('SELECT version_num FROM alembic_version'))
            new_version = result.fetchone()
            
            if new_version and new_version[0] == latest_revision:
                print(f"✅ Successfully fixed! Version is now: {new_version[0]}")
                return True
            else:
                print(f"⚠️  Fix verification failed")
                return False
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🔧 Alembic Version Fix Script")
    print("=" * 60)
    
    success = check_and_fix_alembic_version()
    
    print("=" * 60)
    if success:
        print("✅ Alembic version check completed successfully")
        sys.exit(0)
    else:
        print("❌ Alembic version check failed")
        sys.exit(1)

