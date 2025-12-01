"""
Grant 500 tokens to all active premium users after production deployment

This script should be run ONCE after deploying premium tier changes to production
to ensure all existing premium users get bonus tokens as a thank you for being early supporters.

Usage:
    python scripts/grant_premium_tokens_after_deploy.py
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.settings import settings
from app.db.models import User
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def grant_tokens_to_premium_users(dry_run: bool = False):
    """
    Grant 500 tokens to all active premium users AND initialize their temp_energy
    
    Args:
        dry_run: If True, only shows what would be done without making changes
    """
    # Create database connection
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()
    
    # Tier-based temp_energy amounts
    TIER_TEMP_ENERGY = {
        "plus": 50,
        "premium": 75,
        "pro": 100,
        "legendary": 200,
        "free": 0
    }
    
    try:
        # Find all active premium users
        now = datetime.utcnow()
        active_premium_users = db.query(User).filter(
            User.is_premium == True,
            # Either no expiry (lifetime) or not expired yet
            db.or_(
                User.premium_until.is_(None),
                User.premium_until > now
            )
        ).all()
        
        logger.info(f"Found {len(active_premium_users)} active premium users")
        
        if len(active_premium_users) == 0:
            logger.info("No premium users found. Nothing to do.")
            return
        
        tokens_to_grant = 500
        total_tokens_granted = 0
        total_temp_energy_granted = 0
        users_updated = 0
        
        # Process each premium user
        for user in active_premium_users:
            user_info = f"User {user.id} (@{user.username or 'no_username'})"
            current_tokens = user.energy
            new_tokens = current_tokens + tokens_to_grant
            
            # Ensure all existing premium users have "premium" tier
            original_tier = user.premium_tier or "free"
            if user.premium_tier != "premium":
                user.premium_tier = "premium"
                tier_changed = True
            else:
                tier_changed = False
            
            # Get tier-based temp_energy (always "premium" now)
            tier = user.premium_tier
            temp_energy_amount = TIER_TEMP_ENERGY.get(tier, 0)
            
            if dry_run:
                logger.info(
                    f"[DRY RUN] Would update {user_info}:"
                )
                logger.info(
                    f"  • Tokens: {current_tokens} → {new_tokens} (+{tokens_to_grant})"
                )
                if original_tier != "premium":
                    logger.info(
                        f"  • Tier: {original_tier} → premium (upgraded)"
                    )
                logger.info(
                    f"  • Temp energy: {getattr(user, 'temp_energy', 0)} → {temp_energy_amount} (tier: {tier})"
                )
                logger.info(
                    f"  • Set last_temp_energy_refill to now"
                )
            else:
                # Grant permanent tokens
                user.energy = new_tokens
                total_tokens_granted += tokens_to_grant
                
                # Initialize temp_energy if field exists
                if hasattr(user, 'temp_energy') and temp_energy_amount > 0:
                    user.temp_energy = temp_energy_amount
                    total_temp_energy_granted += temp_energy_amount
                    user.last_temp_energy_refill = now
                    logger.info(
                        f"✅ Updated {user_info}:"
                    )
                    if tier_changed:
                        logger.info(
                            f"  • Tier: {original_tier} → premium (set)"
                        )
                    logger.info(
                        f"  • Tokens: {current_tokens} → {new_tokens} (+{tokens_to_grant})"
                    )
                    logger.info(
                        f"  • Temp energy: {temp_energy_amount} (daily, tier: {tier})"
                    )
                else:
                    logger.info(
                        f"✅ Granted {tokens_to_grant} tokens to {user_info} "
                        f"(tier: {tier}, {current_tokens} → {new_tokens})"
                    )
                    if not hasattr(user, 'temp_energy'):
                        logger.warning(
                            f"  ⚠️  temp_energy field not available yet (migration not run?)"
                        )
                
                users_updated += 1
        
        if not dry_run:
            db.commit()
            logger.info("")
            logger.info("="*70)
            logger.info("✅ GRANT COMPLETED SUCCESSFULLY")
            logger.info("="*70)
            logger.info(f"Users updated: {users_updated}")
            logger.info(f"Permanent tokens granted: {total_tokens_granted} ({tokens_to_grant} per user)")
            logger.info(f"Temp energy initialized: {total_temp_energy_granted} total")
            logger.info("")
            logger.info("💡 Temp energy will auto-refill daily:")
            for tier, amount in TIER_TEMP_ENERGY.items():
                if amount > 0:
                    logger.info(f"  • {tier.capitalize()}: {amount} tokens/day")
            logger.info("="*70)
        else:
            logger.info("")
            logger.info("="*70)
            logger.info("[DRY RUN SUMMARY]")
            logger.info("="*70)
            logger.info(f"Would update: {len(active_premium_users)} users")
            logger.info(f"Permanent tokens: {len(active_premium_users) * tokens_to_grant} ({tokens_to_grant} per user)")
            estimated_temp = sum(TIER_TEMP_ENERGY.get(u.premium_tier or "free", 0) for u in active_premium_users)
            logger.info(f"Temp energy total: {estimated_temp}")
            logger.info("")
            logger.info("Run without --dry-run to apply changes")
            logger.info("="*70)
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error granting tokens: {e}", exc_info=True)
        raise
    finally:
        db.close()


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Grant 500 tokens to all active premium users after deployment"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Skip confirmation prompt (USE WITH CAUTION)"
    )
    
    args = parser.parse_args()
    
    # Safety check
    if not args.dry_run and not args.confirm:
        print("\n" + "="*70)
        print("⚠️  WARNING: This script will grant 500 tokens to ALL premium users")
        print("="*70)
        print("\nThis action:")
        print("  • Will modify user token balances in the database")
        print("  • Should only be run ONCE after deployment")
        print("  • Cannot be easily undone")
        print("\nRecommendation: Run with --dry-run first to see what will happen")
        print("\nEnvironment:", "PRODUCTION" if "prod" in settings.DATABASE_URL.lower() else "OTHER")
        print("Database:", settings.DATABASE_URL.split("@")[-1] if "@" in settings.DATABASE_URL else "Unknown")
        print()
        
        response = input("Are you sure you want to proceed? Type 'yes' to continue: ")
        if response.lower() != "yes":
            print("Aborted.")
            return
    
    # Run the script
    if args.dry_run:
        print("\n🔍 Running in DRY RUN mode - no changes will be made\n")
    
    grant_tokens_to_premium_users(dry_run=args.dry_run)
    
    if not args.dry_run:
        print("\n✅ Token grant completed successfully!")
        print("📊 Check logs above for details")


if __name__ == "__main__":
    main()

