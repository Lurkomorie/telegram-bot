"""
Payment handlers for Telegram Stars
"""
from aiogram import types
from aiogram.filters import Command
from app.bot.loader import router, bot
from app.db.base import get_db
from app.db import crud
from app.settings import settings

# ============================================
# 🎄 NEW YEAR SALE - 20% OFF ALL PRICES! 🎄
# ============================================
# To disable sale: change NEW_YEAR_DISCOUNT to 0
NEW_YEAR_DISCOUNT = 0.20  # 20% off

def apply_discount(price: int) -> int:
    """Apply New Year discount to price"""
    return round(price * (1 - NEW_YEAR_DISCOUNT))


STARS_TO_USD = 0.013  # Approximate conversion rate: 1 star ≈ $0.013


async def send_payment_notification(user: types.User, product_id: str, product: dict, db_user=None, purchase_count: int = 0):
    """
    Send payment notification to the configured Telegram group/channel
    
    Args:
        user: Telegram user object
        product_id: Product ID
        product: Product details dict
        db_user: Database user object with acquisition_source
        purchase_count: Total number of purchases by this user
    """
    if not settings.PAYMENT_NOTIFICATION_CHAT_ID:
        return
    
    try:
        # Build user info
        user_link = f"<a href='tg://user?id={user.id}'>{user.full_name}</a>"
        username = f"@{user.username}" if user.username else "no username"
        
        # Build product info
        product_type = product["type"]
        stars_amount = product["stars"]
        usd_amount = round(stars_amount * STARS_TO_USD, 2)
        
        if product_type == "tokens":
            product_desc = f"🪙 {product['amount']} tokens"
        else:
            tier = product["tier"].capitalize()
            duration = product["duration"]
            product_desc = f"👑 {tier} ({duration} days)"
        
        # Build acquisition source info
        acquisition_source = db_user.acquisition_source if db_user and db_user.acquisition_source else "direct"
        
        message = (
            f"💰 <b>New Payment Received!</b>\n\n"
            f"👤 User: {user_link}\n"
            f"🆔 ID: <code>{user.id}</code>\n"
            f"📛 Username: {username}\n\n"
            f"📦 Product: {product_desc}\n"
            f"⭐ Amount: <b>{stars_amount} Stars</b> (~${usd_amount})\n"
            f"🏷️ Product ID: <code>{product_id}</code>\n\n"
            f"📊 Source: <b>{acquisition_source}</b>\n"
            f"🛒 Purchase #: <b>{purchase_count}</b>"
        )
        
        await bot.send_message(
            chat_id=settings.PAYMENT_NOTIFICATION_CHAT_ID,
            text=message,
            parse_mode="HTML"
        )
        print(f"[PAYMENT] ✅ Notification sent to group {settings.PAYMENT_NOTIFICATION_CHAT_ID}")
    except Exception as e:
        print(f"[PAYMENT] ⚠️ Failed to send payment notification: {e}")

# Payment products: token packages and tier subscriptions
# Prices with 20% New Year discount applied
PAYMENT_PRODUCTS = {
    # Token packages (one-time purchases) - 20% OFF
    "tokens_50": {"type": "tokens", "amount": 50, "stars": apply_discount(35)},      # 35 → 28
    "tokens_100": {"type": "tokens", "amount": 100, "stars": apply_discount(70)},    # 70 → 56
    "tokens_250": {"type": "tokens", "amount": 250, "stars": apply_discount(175)},   # 175 → 140
    "tokens_500": {"type": "tokens", "amount": 500, "stars": apply_discount(350)},   # 350 → 280
    "tokens_1000": {"type": "tokens", "amount": 1000, "stars": apply_discount(700)}, # 700 → 560
    "tokens_2500": {"type": "tokens", "amount": 2500, "stars": apply_discount(1750)}, # 1750 → 1400
    "tokens_5000": {"type": "tokens", "amount": 5000, "stars": apply_discount(3500)}, # 3500 → 2800
    "tokens_10000": {"type": "tokens", "amount": 10000, "stars": apply_discount(7000)}, # 7000 → 5600
    "tokens_25000": {"type": "tokens", "amount": 25000, "stars": apply_discount(17500)}, # 17500 → 14000
    
    # Tier subscriptions (30 days) - 20% OFF
    "plus_month": {"type": "tier", "tier": "plus", "duration": 30, "stars": apply_discount(450), "daily_tokens": 50},       # 450 → 360
    "pro_month": {"type": "tier", "tier": "pro", "duration": 30, "stars": apply_discount(700), "daily_tokens": 75},         # 700 → 560
    "legendary_month": {"type": "tier", "tier": "legendary", "duration": 30, "stars": apply_discount(900), "daily_tokens": 100}, # 900 → 720
    
    # Tier subscriptions (90 days) - 20% OFF (stacks with duration discount)
    "plus_3months": {"type": "tier", "tier": "plus", "duration": 90, "stars": apply_discount(1215), "daily_tokens": 50},
    "pro_3months": {"type": "tier", "tier": "pro", "duration": 90, "stars": apply_discount(1890), "daily_tokens": 75},
    "legendary_3months": {"type": "tier", "tier": "legendary", "duration": 90, "stars": apply_discount(2430), "daily_tokens": 100},
    
    # Tier subscriptions (180 days) - 20% OFF (stacks with duration discount)
    "plus_6months": {"type": "tier", "tier": "plus", "duration": 180, "stars": apply_discount(1890), "daily_tokens": 50},
    "pro_6months": {"type": "tier", "tier": "pro", "duration": 180, "stars": apply_discount(2940), "daily_tokens": 75},
    "legendary_6months": {"type": "tier", "tier": "legendary", "duration": 180, "stars": apply_discount(3780), "daily_tokens": 100},
    
    # Tier subscriptions (365 days) - 20% OFF (stacks with duration discount)
    "plus_year": {"type": "tier", "tier": "plus", "duration": 365, "stars": apply_discount(3780), "daily_tokens": 50},
    "pro_year": {"type": "tier", "tier": "pro", "duration": 365, "stars": apply_discount(5880), "daily_tokens": 75},
    "legendary_year": {"type": "tier", "tier": "legendary", "duration": 365, "stars": apply_discount(7560), "daily_tokens": 100},
}


def process_payment_transaction(db, user_id: int, product_id: str, telegram_payment_charge_id: str = None) -> dict:
    """
    Shared payment processing logic for both real and simulated payments
    
    Args:
        db: Database session
        user_id: Telegram user ID
        product_id: Product ID from PAYMENT_PRODUCTS
        telegram_payment_charge_id: Payment charge ID from Telegram (None for simulated)
    
    Returns:
        dict with keys: success (bool), message (str), tokens (int), tier (str), premium_until (str)
    """
    # Get product details
    if product_id not in PAYMENT_PRODUCTS:
        return {
            "success": False,
            "message": "Invalid product",
            "error": "invalid_product"
        }
    
    product = PAYMENT_PRODUCTS[product_id]
    product_type = product["type"]
    
    if product_type == "tokens":
        # Token package purchase
        tokens_amount = product["amount"]
        success = crud.add_user_energy(db, user_id, tokens_amount)
        
        if success:
            # Create transaction record
            crud.create_payment_transaction(
                db=db,
                user_id=user_id,
                transaction_type="token_package",
                product_id=product_id,
                amount_stars=product["stars"],
                tokens_received=tokens_amount,
                telegram_payment_charge_id=telegram_payment_charge_id
            )
            
            # Get updated balance
            user = crud.get_or_create_user(db, user_id)
            
            return {
                "success": True,
                "message": f"🪙 <b>Tokens Purchased!</b>\n\n✨ +{tokens_amount} tokens added to your account!\n💰 Current balance: <b>{user.energy} tokens</b>\n\nThank you for your purchase! 💎",
                "tokens": user.energy,
                "tier": None
            }
        else:
            return {
                "success": False,
                "message": "Failed to add tokens. Please contact support.",
                "error": "add_tokens_failed"
            }
    
    elif product_type == "tier":
        # Tier subscription purchase
        tier = product["tier"]
        duration_days = product["duration"]
        daily_tokens = product["daily_tokens"]
        
        success = crud.activate_premium(db, user_id, duration_days, tier)
        
        if success:
            # Create transaction record
            crud.create_payment_transaction(
                db=db,
                user_id=user_id,
                transaction_type="tier_subscription",
                product_id=product_id,
                amount_stars=product["stars"],
                tier_granted=tier,
                subscription_days=duration_days,
                telegram_payment_charge_id=telegram_payment_charge_id
            )
            
            # Get updated user info
            user = crud.get_or_create_user(db, user_id)
            premium_until = user.premium_until.strftime("%Y-%m-%d") if user.premium_until else "Forever"
            
            tier_names = {
                "plus": "Plus",
                "premium": "Premium",
                "pro": "Pro",
                "legendary": "Legendary"
            }
            tier_display = tier_names.get(tier, tier.capitalize())
            
            return {
                "success": True,
                "message": f"🎉 <b>Welcome to {tier_display}!</b>\n\n✨ Your {tier_display} subscription is now active!\n📅 Valid until: <b>{premium_until}</b>\n\nBenefits:\n🪙 +{daily_tokens} tokens every day\n🎁 Daily bonus rewards\n🚀 Enjoy the full experience!\n\nThank you for your support! 💎",
                "tokens": user.energy,
                "tier": tier,
                "premium_until": premium_until
            }
        else:
            return {
                "success": False,
                "message": "Failed to activate subscription. Please contact support.",
                "error": "activate_premium_failed"
            }
    
    return {
        "success": False,
        "message": "Unknown product type",
        "error": "unknown_product_type"
    }



@router.pre_checkout_query()
async def pre_checkout_query_handler(pre_checkout_query: types.PreCheckoutQuery):
    """
    Handle pre-checkout query - validate payment before processing
    This is called by Telegram before charging the user
    """
    # Always approve - we validate on successful payment
    await pre_checkout_query.answer(ok=True)


@router.message(lambda message: message.successful_payment)
async def successful_payment_handler(message: types.Message):
    """
    Handle successful payment - process token package or tier subscription
    """
    payment = message.successful_payment
    user_id = message.from_user.id
    
    # Extract product_id from invoice payload
    product_id = payment.invoice_payload
    
    print(f"[PAYMENT] ✅ Successful payment from user {user_id}, product: {product_id}")
    print(f"[PAYMENT] Amount: {payment.total_amount} {payment.currency}")
    
    with get_db() as db:
        result = process_payment_transaction(
            db,
            user_id,
            product_id,
            telegram_payment_charge_id=payment.telegram_payment_charge_id
        )
        
        if result["success"]:
            await message.answer(result["message"])
            print(f"[PAYMENT] ✅ Payment processed successfully for user {user_id}")
            
            # Send notification to payment group
            if product_id in PAYMENT_PRODUCTS:
                # Get user and purchase count for notification
                db_user = crud.get_or_create_user(db, user_id)
                purchase_count = crud.get_user_purchase_count(db, user_id)
                
                await send_payment_notification(
                    user=message.from_user,
                    product_id=product_id,
                    product=PAYMENT_PRODUCTS[product_id],
                    db_user=db_user,
                    purchase_count=purchase_count
                )
        else:
            await message.answer(f"❌ {result['message']}")
            print(f"[PAYMENT] ❌ Payment processing failed for user {user_id}: {result.get('error')}")


@router.message(Command("premium_status"))
async def cmd_premium_status(message: types.Message):
    """Check premium subscription status"""
    user_id = message.from_user.id
    
    with get_db() as db:
        is_premium = crud.check_user_premium(db, user_id)["is_premium"]
        user = crud.get_or_create_user(db, user_id)
        
        if is_premium:
            premium_until = user.premium_until.strftime("%Y-%m-%d %H:%M UTC") if user.premium_until else "Forever"
            await message.answer(
                f"💎 <b>Premium Status</b>\n\n"
                f"✨ You have an active premium subscription!\n"
                f"📅 Valid until: <b>{premium_until}</b>\n\n"
                f"Benefits:\n"
                f"⚡ Unlimited energy\n"
                f"📸 Free image generation"
            )
        else:
            energy_info = crud.get_user_energy(db, user_id)
            await message.answer(
                f"🆓 <b>Free Account</b>\n\n"
                f"⚡ Energy: {energy_info['energy']}/{energy_info['max_energy']}\n"
                f"🔄 You receive +10 energy daily\n\n"
                f"💎 Upgrade to Premium for unlimited energy!\n"
                f"Use /start to access the premium plans."
            )

