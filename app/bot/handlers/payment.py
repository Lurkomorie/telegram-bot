"""
Payment handlers for Telegram Stars
"""
from aiogram import types
from aiogram.filters import Command
from app.bot.loader import router, bot
from app.db.base import get_db
from app.db import crud
from app.settings import settings

# Stars to USD conversion rate
STARS_TO_USD = 0.02  # 1 star ≈ $0.02


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
        
        if product_type == "subscription":
            period = product["period"]
            duration = product["duration"]
            product_desc = f"👑 Premium ({period}, {duration} days)"
        else:
            product_desc = f"Unknown: {product_id}"
        
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


async def send_payment_error_notification(
    user: types.User, 
    product_id: str, 
    charge_id: str,
    error_type: str,
    error_message: str,
    amount: int = None
):
    """
    Send payment ERROR notification to the configured Telegram group/channel
    
    Args:
        user: Telegram user object
        product_id: Product ID
        charge_id: Telegram payment charge ID
        error_type: Type of error (e.g., 'processing_failed', 'exception', 'user_not_found')
        error_message: Detailed error message
        amount: Payment amount in stars (optional)
    """
    if not settings.PAYMENT_NOTIFICATION_CHAT_ID:
        return
    
    try:
        # Build user info
        user_link = f"<a href='tg://user?id={user.id}'>{user.full_name}</a>"
        username = f"@{user.username}" if user.username else "no username"
        
        # Get product info if available
        product = PAYMENT_PRODUCTS.get(product_id)
        if product:
            stars_amount = product["stars"]
            usd_amount = round(stars_amount * STARS_TO_USD, 2)
            if product["type"] == "subscription":
                period = product["period"]
                duration = product["duration"]
                product_desc = f"👑 Premium ({period}, {duration} days)"
            else:
                product_desc = f"Unknown: {product_id}"
        else:
            stars_amount = amount or "?"
            usd_amount = round(amount * STARS_TO_USD, 2) if amount else "?"
            product_desc = f"Unknown product: {product_id}"
        
        message = (
            f"🚨 <b>PAYMENT ERROR!</b> 🚨\n\n"
            f"👤 User: {user_link}\n"
            f"🆔 ID: <code>{user.id}</code>\n"
            f"📛 Username: {username}\n\n"
            f"📦 Product: {product_desc}\n"
            f"⭐ Amount: <b>{stars_amount} Stars</b> (~${usd_amount})\n"
            f"🏷️ Product ID: <code>{product_id}</code>\n"
            f"🔑 Charge ID: <code>{charge_id}</code>\n\n"
            f"❌ Error Type: <b>{error_type}</b>\n"
            f"📝 Details: <code>{error_message[:500]}</code>\n\n"
            f"⚠️ <b>User paid but may not have received product!</b>\n"
            f"🔧 <b>Manual intervention required!</b>"
        )
        
        await bot.send_message(
            chat_id=settings.PAYMENT_NOTIFICATION_CHAT_ID,
            text=message,
            parse_mode="HTML"
        )
        print(f"[PAYMENT] 🚨 Error notification sent to group {settings.PAYMENT_NOTIFICATION_CHAT_ID}")
    except Exception as e:
        print(f"[PAYMENT] ⚠️ Failed to send payment error notification: {e}")

# Payment products: Unified subscription system
# Four periods with same benefits, different durations and prices
PAYMENT_PRODUCTS = {
    # Token packages - New Year Sale 20% off
    "tokens_50": {
        "type": "tokens",
        "amount": 50,
        "stars": 28,  # 20% off from 35
        "original_stars": 35
    },
    "tokens_100": {
        "type": "tokens",
        "amount": 100,
        "stars": 52,  # 20% off from 65
        "original_stars": 65
    },
    "tokens_250": {
        "type": "tokens",
        "amount": 250,
        "stars": 120,  # 20% off from 150
        "original_stars": 150
    },
    "tokens_500": {
        "type": "tokens",
        "amount": 500,
        "stars": 240,  # 20% off from 300
        "original_stars": 300
    },
    "tokens_1000": {
        "type": "tokens",
        "amount": 1000,
        "stars": 480,  # 20% off from 600
        "original_stars": 600
    },
    "tokens_2500": {
        "type": "tokens",
        "amount": 2500,
        "stars": 1120,  # 20% off from 1400
        "original_stars": 1400
    },
    "tokens_5000": {
        "type": "tokens",
        "amount": 5000,
        "stars": 2160,  # 20% off from 2700
        "original_stars": 2700
    },
    "tokens_10000": {
        "type": "tokens",
        "amount": 10000,
        "stars": 4000,  # 20% off from 5000
        "original_stars": 5000
    },
    "tokens_25000": {
        "type": "tokens",
        "amount": 25000,
        "stars": 9600,  # 20% off from 12000
        "original_stars": 12000
    },
    
    # Daily subscription - no discount
    "subscription_daily": {
        "type": "subscription",
        "period": "day",
        "duration": 1,
        "stars": 95,
        "original_stars": None  # No discount shown
    },
    # Weekly subscription - 41% off (was 500 stars / $10)
    "subscription_weekly": {
        "type": "subscription",
        "period": "week",
        "duration": 7,
        "stars": 295,
        "original_stars": 500  # -41% discount
    },
    # Monthly subscription - 78% off (was 2500 stars), Most Popular
    "subscription_monthly": {
        "type": "subscription",
        "period": "month",
        "duration": 30,
        "stars": 495,
        "original_stars": 2500  # -78% discount
    },
    # Yearly subscription - 92% off (was 30000 stars)
    "subscription_yearly": {
        "type": "subscription",
        "period": "year",
        "duration": 365,
        "stars": 2495,
        "original_stars": 30000  # -92% discount
    }
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
        dict with keys: success (bool), message (str), tier (str), premium_until (str)
    """
    print(f"[PAYMENT-TX] 🔄 Processing transaction for user {user_id}, product {product_id}")
    
    # Get product details
    if product_id not in PAYMENT_PRODUCTS:
        print(f"[PAYMENT-TX] ❌ Invalid product ID: {product_id}")
        return {
            "success": False,
            "message": "Invalid product",
            "error": "invalid_product"
        }
    
    product = PAYMENT_PRODUCTS[product_id]
    product_type = product["type"]
    
    # Verify user exists first
    user = crud.get_user(db, user_id)
    if not user:
        print(f"[PAYMENT-TX] ❌ User {user_id} not found in database!")
        return {
            "success": False,
            "message": "User not found. Please contact support.",
            "error": "user_not_found"
        }
    print(f"[PAYMENT-TX] 👤 User found: {user_id}, current premium: {user.is_premium}")
    
    if product_type == "subscription":
        # Unified subscription purchase - all periods give same benefits
        duration_days = product["duration"]
        period = product["period"]
        
        print(f"[PAYMENT-TX] 👑 Activating subscription for {duration_days} days ({period}) for user {user_id}")
        # All subscriptions use "premium" tier - no tier distinctions
        success = crud.activate_premium(db, user_id, duration_days, "premium")
        
        if success:
            print(f"[PAYMENT-TX] ✅ Subscription activated successfully")
            # Create transaction record
            crud.create_payment_transaction(
                db=db,
                user_id=user_id,
                transaction_type="tier_subscription",
                product_id=product_id,
                amount_stars=product["stars"],
                tier_granted="premium",
                subscription_days=duration_days,
                telegram_payment_charge_id=telegram_payment_charge_id
            )
            print(f"[PAYMENT-TX] 📝 Transaction record created")
            
            # Get updated user info
            user = crud.get_or_create_user(db, user_id)
            print(f"[PAYMENT-TX] 👤 User updated: premium_until={user.premium_until}")
            premium_until = user.premium_until.strftime("%Y-%m-%d") if user.premium_until else "Forever"
            
            period_names = {
                "day": "1 Day",
                "week": "1 Week",
                "month": "1 Month",
                "year": "1 Year"
            }
            period_display = period_names.get(period, period.capitalize())
            
            return {
                "success": True,
                "message": f"🎉 <b>Premium Activated!</b>\n\n✨ Your {period_display} subscription is now active!\n📅 Valid until: <b>{premium_until}</b>\n\nBenefits:\n♾️ Unlimited energy\n🔞 No blur\n🎭 Enhanced AI\n🧠 Enhanced memory\n\nThank you for your support! 💎",
                "tier": "premium",
                "premium_until": premium_until
            }
        else:
            print(f"[PAYMENT-TX] ❌ Failed to activate subscription for user {user_id}")
            return {
                "success": False,
                "message": "Failed to activate subscription. Please contact support.",
                "error": "activate_subscription_failed"
            }
    
    elif product_type == "tokens":
        # Token package purchase
        token_amount = product["amount"]
        
        print(f"[PAYMENT-TX] ⚡ Adding {token_amount} tokens to user {user_id}")
        success = crud.add_user_energy(db, user_id, token_amount)
        
        if success:
            print(f"[PAYMENT-TX] ✅ Tokens added successfully")
            # Create transaction record
            crud.create_payment_transaction(
                db=db,
                user_id=user_id,
                transaction_type="token_package",
                product_id=product_id,
                amount_stars=product["stars"],
                tokens_received=token_amount,
                telegram_payment_charge_id=telegram_payment_charge_id
            )
            print(f"[PAYMENT-TX] 📝 Transaction record created")
            
            # Get updated user info
            user = crud.get_or_create_user(db, user_id)
            total_tokens = (user.temp_energy or 0) + user.energy
            print(f"[PAYMENT-TX] 👤 User updated: total_tokens={total_tokens}")
            
            return {
                "success": True,
                "message": f"🎉 <b>Tokens Added!</b>\n\n⚡ You received <b>{token_amount}</b> tokens!\n💰 Your balance: <b>{total_tokens}</b> tokens\n\nThank you for your support! 💎",
                "tokens_granted": token_amount,
                "total_tokens": total_tokens
            }
        else:
            print(f"[PAYMENT-TX] ❌ Failed to add tokens for user {user_id}")
            return {
                "success": False,
                "message": "Failed to add tokens. Please contact support.",
                "error": "add_tokens_failed"
            }
    
    print(f"[PAYMENT-TX] ❌ Unknown product type: {product_type}")
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
    import traceback
    
    payment = message.successful_payment
    user_id = message.from_user.id
    
    # Extract product_id from invoice payload
    product_id = payment.invoice_payload
    
    print(f"[PAYMENT] ✅ Successful payment from user {user_id}, product: {product_id}")
    print(f"[PAYMENT] Amount: {payment.total_amount} {payment.currency}")
    print(f"[PAYMENT] Telegram charge ID: {payment.telegram_payment_charge_id}")
    
    try:
        with get_db() as db:
            # CRITICAL: Ensure user exists before processing payment
            # This handles edge case where user pays via miniapp deep link without /start
            db_user = crud.get_or_create_user(
                db, 
                user_id, 
                username=message.from_user.username,
                first_name=message.from_user.first_name
            )
            print(f"[PAYMENT] 👤 User ensured in DB: {user_id} (premium_tier: {db_user.premium_tier})")
            
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
                    # Refresh user data for notification
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
                error_msg = result.get('error', 'unknown_error')
                await message.answer(f"❌ {result['message']}")
                print(f"[PAYMENT] ❌ Payment processing failed for user {user_id}: {error_msg}")
                
                # Log critical payment failure for manual intervention
                print(f"[PAYMENT] ⚠️ CRITICAL: User {user_id} paid but processing failed!")
                print(f"[PAYMENT] ⚠️ Product: {product_id}, Charge ID: {payment.telegram_payment_charge_id}")
                print(f"[PAYMENT] ⚠️ Error: {error_msg}")
                
                # Send error notification to payment group
                await send_payment_error_notification(
                    user=message.from_user,
                    product_id=product_id,
                    charge_id=payment.telegram_payment_charge_id or "N/A",
                    error_type="processing_failed",
                    error_message=error_msg,
                    amount=payment.total_amount
                )
                
    except Exception as e:
        # CRITICAL: Log full traceback for payment failures
        print(f"[PAYMENT] ❌❌ EXCEPTION processing payment for user {user_id}!")
        print(f"[PAYMENT] ❌❌ Product: {product_id}, Charge ID: {payment.telegram_payment_charge_id}")
        print(f"[PAYMENT] ❌❌ Exception: {type(e).__name__}: {e}")
        traceback.print_exc()
        
        # Send error notification to payment group
        try:
            await send_payment_error_notification(
                user=message.from_user,
                product_id=product_id,
                charge_id=payment.telegram_payment_charge_id or "N/A",
                error_type="exception",
                error_message=f"{type(e).__name__}: {e}",
                amount=payment.total_amount
            )
        except Exception as notify_err:
            print(f"[PAYMENT] ⚠️ Failed to send error notification: {notify_err}")
        
        # Notify user of error
        try:
            await message.answer(
                "❌ There was an error processing your payment. "
                "Don't worry - your payment was received! "
                "Please contact support and we'll resolve this immediately."
            )
        except:
            pass
        
        # Re-raise to ensure the error is logged at webhook level too
        raise


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

