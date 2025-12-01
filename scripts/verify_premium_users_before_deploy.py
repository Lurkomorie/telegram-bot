"""
Verify premium users status before production deployment

This script checks the current state of premium users and helps ensure
a safe deployment. Run this BEFORE merging to production.

Usage:
    python scripts/verify_premium_users_before_deploy.py
"""
import sys
from pathlib import Path
from datetime import datetime
from collections import Counter

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.settings import settings
from app.db.models import User


def verify_premium_users():
    """Verify current state of premium users"""
    # Create database connection
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()
    
    try:
        print("\n" + "="*70)
        print("🔍 PREMIUM USERS VERIFICATION REPORT")
        print("="*70 + "\n")
        
        # Database info
        db_host = settings.DATABASE_URL.split("@")[-1] if "@" in settings.DATABASE_URL else "Unknown"
        print(f"📊 Database: {db_host}")
        print(f"🕐 Report time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n")
        
        # Total users
        total_users = db.query(User).count()
        print(f"👥 Total users: {total_users}")
        
        # Premium users
        now = datetime.utcnow()
        all_premium_marked = db.query(User).filter(User.is_premium == True).all()
        
        # Categorize premium users
        active_premium = []
        expired_premium = []
        lifetime_premium = []
        
        for user in all_premium_marked:
            if user.premium_until is None:
                lifetime_premium.append(user)
            elif user.premium_until > now:
                active_premium.append(user)
            else:
                expired_premium.append(user)
        
        print(f"💎 Premium users (is_premium=True): {len(all_premium_marked)}")
        print(f"   ├─ Active (not expired): {len(active_premium)}")
        print(f"   ├─ Lifetime (no expiry): {len(lifetime_premium)}")
        print(f"   └─ Expired: {len(expired_premium)}")
        
        # Check if premium_tier column exists
        try:
            has_tier_column = hasattr(User, 'premium_tier')
            if has_tier_column:
                print(f"\n✅ premium_tier column exists in database")
                
                # Count by tier
                tier_counts = Counter([u.premium_tier for u in all_premium_marked])
                print(f"\n📊 Premium users by tier:")
                for tier, count in tier_counts.most_common():
                    print(f"   {tier}: {count} users")
            else:
                print(f"\n⚠️  premium_tier column does NOT exist yet")
                print(f"   This is expected before migration 022")
        except Exception as e:
            print(f"\n⚠️  Could not check premium_tier: {e}")
        
        # Token/energy statistics
        print(f"\n💰 Token/Energy statistics:")
        all_energies = [u.energy for u in all_premium_marked]
        if all_energies:
            avg_energy = sum(all_energies) / len(all_energies)
            min_energy = min(all_energies)
            max_energy = max(all_energies)
            print(f"   Average: {avg_energy:.0f} tokens")
            print(f"   Min: {min_energy} tokens")
            print(f"   Max: {max_energy} tokens")
        
        # Sample premium users (first 10 active)
        print(f"\n👤 Sample active premium users:")
        for i, user in enumerate(active_premium[:10], 1):
            tier = getattr(user, 'premium_tier', 'unknown')
            expiry = user.premium_until.strftime('%Y-%m-%d') if user.premium_until else 'lifetime'
            print(f"   {i}. User {user.id} (@{user.username or 'no_username'})")
            print(f"      Tokens: {user.energy}, Tier: {tier}, Expires: {expiry}")
        
        if len(active_premium) > 10:
            print(f"   ... and {len(active_premium) - 10} more")
        
        # Warnings
        print(f"\n⚠️  WARNINGS:")
        warnings = []
        
        if len(expired_premium) > 0:
            warnings.append(
                f"   • {len(expired_premium)} users have is_premium=True but expired premium_until"
            )
        
        if has_tier_column:
            free_tier_premium = [u for u in all_premium_marked if u.premium_tier == "free"]
            if free_tier_premium:
                warnings.append(
                    f"   • {len(free_tier_premium)} users have is_premium=True but tier='free'"
                )
        
        if not warnings:
            print("   ✅ No warnings! Everything looks good.")
        else:
            for warning in warnings:
                print(warning)
        
        # Expected impact
        print(f"\n📈 EXPECTED IMPACT OF TOKEN GRANT:")
        token_grant = 500
        active_count = len(active_premium) + len(lifetime_premium)
        total_tokens_to_grant = active_count * token_grant
        print(f"   Active premium users to receive tokens: {active_count}")
        print(f"   Tokens per user: {token_grant}")
        print(f"   Total tokens to be granted: {total_tokens_to_grant:,}")
        
        if all_energies:
            new_avg_energy = (sum(all_energies) + total_tokens_to_grant) / len(all_energies)
            print(f"   Average tokens after grant: {new_avg_energy:.0f}")
        
        # Recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        print("   1. ✅ Create database backup before deployment")
        print("   2. ✅ Test migrations on staging/local copy first")
        print("   3. ✅ Run token grant script in --dry-run mode first")
        print("   4. ✅ Monitor logs during and after deployment")
        print("   5. ✅ Send thank you message to premium users after token grant")
        
        print("\n" + "="*70)
        print("✅ Verification complete!")
        print("="*70 + "\n")
        
        return {
            "total_users": total_users,
            "active_premium": len(active_premium) + len(lifetime_premium),
            "expired_premium": len(expired_premium),
            "has_tier_column": has_tier_column,
            "total_tokens_to_grant": total_tokens_to_grant
        }
        
    except Exception as e:
        print(f"\n❌ ERROR during verification: {e}\n")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()


def main():
    """Main entry point"""
    try:
        verify_premium_users()
    except Exception as e:
        print(f"Failed to verify premium users: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

