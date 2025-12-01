"""
Check production database state before deploying premium changes
Uses raw SQL to avoid schema conflicts with ORM models
"""
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from app.settings import settings


def check_production_state():
    """Check current production state using raw SQL"""
    engine = create_engine(settings.DATABASE_URL)
    
    print("\n" + "="*70)
    print("🔍 PRODUCTION DATABASE CHECK - BEFORE DEPLOYMENT")
    print("="*70 + "\n")
    
    db_host = settings.DATABASE_URL.split("@")[-1] if "@" in settings.DATABASE_URL else "Unknown"
    print(f"📊 Database: {db_host}")
    print(f"🕐 Check time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n")
    
    with engine.connect() as conn:
        # Check what columns exist in users table
        print("📋 CURRENT USERS TABLE COLUMNS:")
        result = conn.execute(text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'users'
            ORDER BY ordinal_position
        """))
        
        columns = {}
        for row in result:
            columns[row[0]] = row[1]
            
        # Check for new fields
        new_fields = {
            'premium_tier': '❌ NOT EXISTS (будет добавлен миграцией 022)',
            'temp_energy': '❌ NOT EXISTS (будет добавлен миграцией 024)',
            'last_temp_energy_refill': '❌ NOT EXISTS (будет добавлен миграцией 024)',
            'daily_bonus_streak': '❌ NOT EXISTS (будет добавлен миграцией 023)',
            'referred_by_user_id': '❌ NOT EXISTS (будет добавлен миграцией 022)',
            'referral_tokens_awarded': '❌ NOT EXISTS (будет добавлен миграцией 022)',
            'max_energy': '❓ CHECKING...'
        }
        
        for field in new_fields:
            if field in columns:
                new_fields[field] = f'✅ EXISTS ({columns[field]})'
        
        print("\n🔍 New fields status:")
        for field, status in new_fields.items():
            print(f"   {field}: {status}")
        
        # Check premium users (using only fields that should exist)
        print("\n💎 PREMIUM USERS CHECK:")
        
        try:
            result = conn.execute(text("""
                SELECT COUNT(*) as total
                FROM users
            """))
            total_users = result.fetchone()[0]
            print(f"   Total users: {total_users}")
        except Exception as e:
            print(f"   ❌ Error counting users: {e}")
            return
        
        try:
            # Check if premium fields exist
            if 'is_premium' not in columns:
                print("   ⚠️  is_premium column doesn't exist yet")
                return
            
            result = conn.execute(text("""
                SELECT COUNT(*) as premium_count
                FROM users
                WHERE is_premium = true
            """))
            premium_marked = result.fetchone()[0]
            print(f"   Users with is_premium=true: {premium_marked}")
            
            # Check active premium (not expired)
            if 'premium_until' in columns:
                result = conn.execute(text("""
                    SELECT COUNT(*) as active_count
                    FROM users
                    WHERE is_premium = true 
                      AND (premium_until IS NULL OR premium_until > NOW())
                """))
                active_premium = result.fetchone()[0]
                print(f"   Active premium (not expired): {active_premium}")
                
                # Get sample premium users
                result = conn.execute(text("""
                    SELECT id, username, energy, premium_until, is_premium
                    FROM users
                    WHERE is_premium = true 
                      AND (premium_until IS NULL OR premium_until > NOW())
                    LIMIT 10
                """))
                
                print(f"\n👤 Sample active premium users:")
                for i, row in enumerate(result, 1):
                    user_id, username, energy, premium_until, is_premium = row
                    expiry = premium_until.strftime('%Y-%m-%d') if premium_until else 'lifetime'
                    print(f"   {i}. User {user_id} (@{username or 'no_username'})")
                    print(f"      Tokens: {energy}, Expires: {expiry}")
                
                # Calculate tokens to grant
                print(f"\n📈 EXPECTED TOKEN GRANT:")
                tokens_per_user = 500
                total_tokens = active_premium * tokens_per_user
                print(f"   Users to receive tokens: {active_premium}")
                print(f"   Tokens per user: {tokens_per_user}")
                print(f"   Total tokens to grant: {total_tokens:,}")
                
                # Calculate average before/after
                result = conn.execute(text("""
                    SELECT AVG(energy) as avg_energy
                    FROM users
                    WHERE is_premium = true 
                      AND (premium_until IS NULL OR premium_until > NOW())
                """))
                avg_energy = result.fetchone()[0]
                if avg_energy:
                    print(f"   Average tokens now: {avg_energy:.0f}")
                    print(f"   Average tokens after grant: {avg_energy + tokens_per_user:.0f}")
                
        except Exception as e:
            print(f"   ❌ Error checking premium users: {e}")
            import traceback
            traceback.print_exc()
        
        # Check current migration version
        print(f"\n🔄 MIGRATION STATUS:")
        try:
            result = conn.execute(text("""
                SELECT version_num
                FROM alembic_version
                LIMIT 1
            """))
            current_version = result.fetchone()
            if current_version:
                print(f"   Current migration: {current_version[0]}")
            else:
                print(f"   ⚠️  No migration version found")
        except Exception as e:
            print(f"   ❌ Error checking migration: {e}")
        
        # Check if payment_transactions table exists
        print(f"\n📊 NEW TABLES CHECK:")
        new_tables = [
            'payment_transactions',
            'system_message_templates',
            'system_messages',
            'system_message_deliveries'
        ]
        
        for table in new_tables:
            result = conn.execute(text("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_name = :table_name
            """), {"table_name": table})
            exists = result.fetchone()[0] > 0
            status = "✅ EXISTS" if exists else "❌ NOT EXISTS (будет создана)"
            print(f"   {table}: {status}")
    
    print("\n" + "="*70)
    print("✅ Production check complete!")
    print("="*70 + "\n")
    
    print("📝 NEXT STEPS:")
    print("1. ✅ Create database backup:")
    print("   railway run pg_dump > backup_$(date +%Y%m%d_%H%M%S).sql")
    print("\n2. ✅ Merge to main and deploy")
    print("\n3. ✅ After deploy, grant tokens:")
    print("   python scripts/grant_premium_tokens_after_deploy.py --dry-run")
    print("   python scripts/grant_premium_tokens_after_deploy.py")
    print()


if __name__ == "__main__":
    try:
        check_production_state()
    except Exception as e:
        print(f"\n❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

