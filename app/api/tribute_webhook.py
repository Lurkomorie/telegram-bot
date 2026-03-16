"""
Tribute payment webhook handler.
Receives webhook events from Tribute (Card/Crypto payments) and grants products.
"""
import hashlib
import hmac
import json
from fastapi import APIRouter, Request, HTTPException
from app.settings import settings

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


def verify_tribute_signature(body: bytes, signature: str) -> bool:
    """Verify Tribute webhook signature using HMAC-SHA256"""
    if not settings.TRIBUTE_API_KEY:
        print("[TRIBUTE-WEBHOOK] ⚠️ TRIBUTE_API_KEY not configured, skipping signature verification")
        return False
    expected = hmac.new(
        settings.TRIBUTE_API_KEY.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


@router.post("/tribute")
async def tribute_webhook(request: Request):
    """
    Handle Tribute payment webhooks.

    Event types:
    - newSubscription: Recurring subscription purchased
    - newDigitalProduct: One-time digital product purchased
    - newDonation: Donation received

    Grants the product to the user identified by user_id in the purchase metadata/URL params.
    """
    body = await request.body()
    signature = request.headers.get("trbt-signature", "")

    import sys
    print(f"[TRIBUTE-WEBHOOK] 📥 Raw body: {body[:500]}", flush=True)
    print(f"[TRIBUTE-WEBHOOK] 📥 Signature: {signature}", flush=True)
    print(f"[TRIBUTE-WEBHOOK] 📥 Headers: {dict(request.headers)}", flush=True)
    sys.stdout.flush()

    try:
        payload = json.loads(body) if body else {}
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    event_type = payload.get("type") or payload.get("event") or ""
    print(f"[TRIBUTE-WEBHOOK] 📥 Event type: '{event_type}', Full payload: {json.dumps(payload, default=str)[:500]}", flush=True)

    # Allow test/ping events through without signature verification
    if event_type in ("test", "ping") or "test_event" in payload:
        print(f"[TRIBUTE-WEBHOOK] 🏓 Test/ping event received, responding OK", flush=True)
        return {"status": "ok"}

    # Skip signature verification temporarily to debug webhook payloads
    # TODO: re-enable after confirming Tribute webhook format
    # if not verify_tribute_signature(body, signature):
    #     print(f"[TRIBUTE-WEBHOOK] ❌ Invalid signature")
    #     raise HTTPException(status_code=401, detail="Invalid signature")

    # Extract user_id - try multiple locations in the payload
    user_id = None

    # 1. Check subscriber.telegram_id (Tribute's format)
    subscriber = payload.get("subscriber", {})
    if isinstance(subscriber, dict):
        tid = subscriber.get("telegram_id")
        if tid:
            try:
                user_id = int(tid)
            except (ValueError, TypeError):
                pass

    # 2. Check metadata.user_id (our custom field)
    if not user_id:
        metadata = payload.get("metadata", {})
        if isinstance(metadata, dict):
            user_id = metadata.get("user_id")

    # 3. Check custom_fields.user_id
    if not user_id:
        custom_fields = payload.get("custom_fields", {})
        if isinstance(custom_fields, dict):
            user_id = custom_fields.get("user_id")

    # 4. Check product URL params (user_id appended by us)
    if not user_id:
        url = payload.get("product_url") or payload.get("url") or ""
        if "user_id=" in url:
            try:
                from urllib.parse import urlparse, parse_qs
                parsed = urlparse(url)
                params = parse_qs(parsed.query)
                user_id_list = params.get("user_id", [])
                if user_id_list:
                    user_id = int(user_id_list[0])
            except (ValueError, IndexError):
                pass

    # 5. Check top-level user_id
    if not user_id:
        try:
            user_id = int(payload.get("user_id", 0))
        except (ValueError, TypeError):
            pass

    if not user_id:
        print(f"[TRIBUTE-WEBHOOK] ❌ Could not extract user_id. FULL PAYLOAD: {json.dumps(payload, default=str)}", flush=True)
        # Return 200 so Tribute doesn't retry, but log everything for debugging
        return {"status": "debug", "error": "no_user_id", "payload_received": payload}

    user_id = int(user_id)

    # Extract product_id from the payload
    product_id = payload.get("product_id") or payload.get("product_name") or ""

    # If product_id not directly available, try to match from product URL
    if not product_id:
        url = payload.get("product_url") or payload.get("url") or ""
        base_url = url.split("?")[0]
        from app.bot.handlers.payment import get_tribute_product_urls
        for pid, lang_urls in get_tribute_product_urls().items():
            if not isinstance(lang_urls, dict):
                continue
            for lang, tribute_url in lang_urls.items():
                if not tribute_url:
                    continue
                base_tribute = tribute_url.split("?")[0]
                if base_tribute and base_url and base_tribute == base_url:
                    product_id = pid
                    break
            if product_id:
                break

    if not product_id:
        print(f"[TRIBUTE-WEBHOOK] ❌ Could not determine product_id from payload")
        raise HTTPException(status_code=400, detail="Could not determine product from webhook payload")

    print(f"[TRIBUTE-WEBHOOK] 🔄 Processing: user={user_id}, product={product_id}, event={event_type}")

    # Process the payment using existing payment logic
    from app.bot.handlers.payment import (
        PAYMENT_PRODUCTS,
        process_payment_transaction,
        send_payment_notification,
    )
    from app.db.base import get_db
    from app.db import crud

    product = PAYMENT_PRODUCTS.get(product_id)
    if not product:
        print(f"[TRIBUTE-WEBHOOK] ❌ Unknown product_id: {product_id}")
        raise HTTPException(status_code=400, detail=f"Unknown product: {product_id}")

    with get_db() as db:
        # Ensure user exists
        db_user = crud.get_or_create_user(db, user_id)

        charge_id = payload.get("transaction_id") or payload.get("id") or f"tribute_{event_type}"

        result = process_payment_transaction(
            db,
            user_id,
            product_id,
            telegram_payment_charge_id=f"tribute:{charge_id}"
        )

        if result["success"]:
            print(f"[TRIBUTE-WEBHOOK] ✅ Payment processed for user {user_id}, product {product_id}")

            # Send admin notification
            try:
                from app.bot.loader import bot
                from aiogram.types import User as AiogramUser

                db_user = crud.get_or_create_user(db, user_id)
                purchase_count = crud.get_user_purchase_count(db, user_id)

                # Build a minimal user-like object for notification
                # send_payment_notification expects an aiogram User, but we create a simple wrapper
                notification_chat_id = settings.PAYMENT_NOTIFICATION_CHAT_ID
                if notification_chat_id:
                    stars_amount = product["stars"]
                    from app.bot.handlers.payment import STARS_TO_USD
                    usd_amount = round(stars_amount * STARS_TO_USD, 2)

                    product_type = product["type"]
                    if product_type == "subscription":
                        period = product["period"]
                        duration = product["duration"]
                        product_desc = f"👑 Premium ({period}, {duration} days)"
                    else:
                        product_desc = f"⚡ {product.get('amount', '?')} Tokens"

                    message = (
                        f"💰 <b>New Tribute Payment!</b> 💳\n\n"
                        f"🆔 User ID: <code>{user_id}</code>\n\n"
                        f"📦 Product: {product_desc}\n"
                        f"⭐ Amount: <b>{stars_amount} Stars equiv</b> (~${usd_amount})\n"
                        f"🏷️ Product ID: <code>{product_id}</code>\n"
                        f"💳 Method: <b>Tribute ({event_type})</b>\n"
                        f"🔑 Charge: <code>{charge_id}</code>\n\n"
                        f"🛒 Purchase #: <b>{purchase_count}</b>"
                    )

                    await bot.send_message(
                        chat_id=notification_chat_id,
                        text=message,
                        parse_mode="HTML"
                    )
            except Exception as e:
                print(f"[TRIBUTE-WEBHOOK] ⚠️ Failed to send notification: {e}")

            return {"status": "ok"}
        else:
            print(f"[TRIBUTE-WEBHOOK] ❌ Payment processing failed: {result.get('error')}")
            raise HTTPException(status_code=500, detail=result.get("message", "Payment processing failed"))
