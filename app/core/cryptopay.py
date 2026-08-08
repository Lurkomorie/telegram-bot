"""
Crypto Pay (@CryptoBot) client: invoices for crypto payments.

Flow: a "crypto" purchase creates an invoice priced in USD and a pending
PaymentTransaction row that remembers the invoice id. Settlement is
double-path — a webhook if the app has one configured in @CryptoBot, and a
scheduler poll as the fallback — funnelled through settle_paid_invoice(),
which is idempotent, so both may fire for the same invoice safely.
"""
import hashlib
import hmac
import json
from typing import Optional

import httpx

from app.settings import settings

API_BASE = "https://pay.crypt.bot/api"

# What a product costs in USD when paid with crypto. Mirrors the Tribute card
# prices (the miniapp's EUR list), NOT the Stars prices — Stars carry their own
# surcharge on purpose.
USD_PRICES = {
    "tokens_50": 0.99,
    "tokens_100": 1.49,
    "tokens_250": 2.99,
    "tokens_500": 4.99,
    "tokens_1000": 8.99,
    "tokens_2500": 19.99,
    "tokens_5000": 34.99,
    "tokens_10000": 59.99,
    "tokens_25000": 129.99,
    "subscription_daily": 1.99,
    "subscription_weekly": 5.99,
    "subscription_monthly": 9.99,
    "subscription_yearly": 49.99,
}


def is_configured() -> bool:
    return bool(settings.CRYPTOPAY_API_TOKEN)


async def _call(method: str, payload: Optional[dict] = None) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{API_BASE}/{method}",
            headers={"Crypto-Pay-API-Token": settings.CRYPTOPAY_API_TOKEN},
            json=payload or {},
        )
        resp.raise_for_status()
        data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(f"CryptoPay {method} failed: {str(data)[:300]}")
    return data["result"]


async def create_invoice(user_id: int, product_id: str, description: str) -> dict:
    """Create a USD-priced invoice payable in any supported asset."""
    amount = USD_PRICES.get(product_id)
    if amount is None:
        raise ValueError(f"No USD price for product {product_id}")
    return await _call("createInvoice", {
        "currency_type": "fiat",
        "fiat": "USD",
        "amount": f"{amount:.2f}",
        "description": description[:1024],
        "payload": f"{user_id}:{product_id}",
        "expires_in": 3600,
    })


async def fetch_invoices(invoice_ids: list) -> list:
    if not invoice_ids:
        return []
    result = await _call("getInvoices", {
        "invoice_ids": ",".join(str(i) for i in invoice_ids),
    })
    return result.get("items", [])


def verify_webhook_signature(body: bytes, signature: str) -> bool:
    """Crypto Pay signs the raw body with HMAC-SHA256, key = SHA256(token)."""
    if not settings.CRYPTOPAY_API_TOKEN or not signature:
        return False
    secret = hashlib.sha256(settings.CRYPTOPAY_API_TOKEN.encode()).digest()
    expected = hmac.new(secret, body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def settle_paid_invoice(db, invoice_id: str, payload: str) -> dict:
    """Credit a paid invoice exactly once and reconcile the tracker row.

    process_payment_transaction creates the canonical completed row and grants
    the benefits; the pending tracker row created at invoice time is then
    removed so revenue is not counted twice. Safe to call repeatedly.
    """
    from app.bot.handlers.payment import process_payment_transaction
    from app.db.models import PaymentTransaction

    already = db.query(PaymentTransaction).filter(
        PaymentTransaction.cryptopay_invoice_id == str(invoice_id),
        PaymentTransaction.status == "completed",
    ).first()
    if already:
        return {"success": True, "message": "already settled"}

    try:
        user_id_str, product_id = payload.split(":", 1)
        user_id = int(user_id_str)
    except (ValueError, AttributeError):
        return {"success": False, "message": f"bad payload: {payload!r}"}

    result = process_payment_transaction(
        db, user_id=user_id, product_id=product_id,
        telegram_payment_charge_id=f"cryptopay:{invoice_id}",
    )
    if result.get("success"):
        canonical = db.query(PaymentTransaction).filter(
            PaymentTransaction.user_id == user_id,
            PaymentTransaction.product_id == product_id,
            PaymentTransaction.status == "completed",
        ).order_by(PaymentTransaction.created_at.desc()).first()
        if canonical:
            canonical.cryptopay_invoice_id = str(invoice_id)
            canonical.payment_provider = "cryptopay"
        db.query(PaymentTransaction).filter(
            PaymentTransaction.cryptopay_invoice_id == str(invoice_id),
            PaymentTransaction.status == "pending",
        ).delete(synchronize_session=False)
        db.commit()
        print(f"[CRYPTOPAY] ✅ Invoice {invoice_id} settled: {product_id} for user {user_id}")
    else:
        print(f"[CRYPTOPAY] ❌ Crediting failed for invoice {invoice_id}: {result.get('message')}")
    return result
