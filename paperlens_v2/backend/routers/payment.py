"""
Payment Router — Cashfree Payments
------------------------------------
Why Cashfree over Razorpay:
  - Individual PAN accepted (no GST/business registration needed)
  - Instant approval (hours, not days)
  - UPI, Cards, NetBanking, Wallets all supported
  - Competitive settlement (T+2)

Flow:
  1. POST /payment/create-order  → Create Cashfree order, return payment_session_id
  2. Frontend loads Cashfree JS SDK with payment_session_id
  3. User pays via UPI / card / netbanking
  4. Cashfree webhook hits POST /payment/webhook (auto-credits user)
  5. Frontend also calls POST /payment/verify as double-check

Credit Packages:
  ₹25  → 1 credit   (single doc)
  ₹150 → 5 credits  (save ₹25)
  ₹500 → 20 credits (save ₹500)
"""

import hmac
import hashlib
import uuid
import httpx
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from database import get_db
from routers.auth import require_auth
from config import get_settings

router = APIRouter()
settings = get_settings()

# Cashfree API base URLs
CASHFREE_PROD_URL = "https://api.cashfree.com/pg"
CASHFREE_TEST_URL = "https://sandbox.cashfree.com/pg"

# Credit packages: id → (amount_rupees, credits, label)
PACKAGES = {
    "starter":  (25,  1,  "1 Analysis — ₹25"),
    "standard": (150, 5,  "5 Analyses — ₹150 (save ₹25)"),
    "pro":      (500, 20, "20 Analyses — ₹500 (save ₹500)"),
}


def _cashfree_base_url() -> str:
    return CASHFREE_TEST_URL if settings.APP_ENV == "development" else CASHFREE_PROD_URL


def _cashfree_headers() -> dict:
    if not settings.CASHFREE_APP_ID or not settings.CASHFREE_SECRET_KEY:
        raise HTTPException(
            status_code=503,
            detail="Payment not configured. Add CASHFREE_APP_ID and CASHFREE_SECRET_KEY to .env",
        )
    return {
        "x-client-id": settings.CASHFREE_APP_ID,
        "x-client-secret": settings.CASHFREE_SECRET_KEY,
        "x-api-version": "2023-08-01",
        "Content-Type": "application/json",
    }


# ── Models ─────────────────────────────────────────────────────────────────────

class CreateOrderRequest(BaseModel):
    package: str  # "starter" | "standard" | "pro"

class VerifyRequest(BaseModel):
    order_id: str  # Cashfree order_id


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/packages")
async def get_packages():
    """Return available credit packages."""
    return {
        "packages": [
            {
                "id": k,
                "amount_rupees": v[0],
                "credits": v[1],
                "label": v[2],
            }
            for k, v in PACKAGES.items()
        ]
    }


@router.post("/create-order")
async def create_order(
    body: CreateOrderRequest,
    current_user: dict = Depends(require_auth),
    db=Depends(get_db),
):
    """
    Create a Cashfree payment order.
    Returns payment_session_id → use with Cashfree JS SDK on frontend.
    """
    package = PACKAGES.get(body.package)
    if not package:
        raise HTTPException(status_code=400, detail=f"Unknown package: {body.package}")

    amount_rupees, credits, label = package

    # Generate our internal order ID (Cashfree requires unique order_id)
    our_order_id = f"pl_{uuid.uuid4().hex[:16]}"

    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(
            f"{_cashfree_base_url()}/orders",
            headers=_cashfree_headers(),
            json={
                "order_id": our_order_id,
                "order_amount": float(amount_rupees),
                "order_currency": "INR",
                "order_note": f"PaperLens {label}",
                "customer_details": {
                    "customer_id": current_user["id"][:50],
                    "customer_email": current_user["email"],
                    "customer_name": current_user.get("name", "User"),
                    "customer_phone": "9999999999",  # required by CF; user can update later
                },
                "order_meta": {
                    "return_url": f"{settings.FRONTEND_URL}/payment/success?order_id={our_order_id}",
                    "notify_url": f"{settings.BACKEND_URL}/payment/webhook",
                },
            },
        )

    if resp.status_code not in (200, 201):
        raise HTTPException(
            status_code=502,
            detail=f"Cashfree error: {resp.text}"
        )

    cf_data = resp.json()
    payment_session_id = cf_data.get("payment_session_id")

    # Save pending transaction in DB
    txn_id = str(uuid.uuid4())
    await db.execute(
        """INSERT INTO transactions
           (id, user_id, payment_ref, amount_paise, credits, status)
           VALUES (?, ?, ?, ?, ?, 'pending')""",
        (txn_id, current_user["id"], our_order_id, amount_rupees * 100, credits),
    )
    await db.commit()

    return {
        "payment_session_id": payment_session_id,
        "order_id": our_order_id,
        "amount_rupees": amount_rupees,
        "credits": credits,
        "label": label,
        # Frontend uses this with Cashfree SDK:
        "cashfree_env": "sandbox" if settings.APP_ENV == "development" else "production",
    }


@router.post("/verify")
async def verify_payment(
    body: VerifyRequest,
    current_user: dict = Depends(require_auth),
    db=Depends(get_db),
):
    """
    Verify payment status by querying Cashfree directly.
    Called by frontend after redirect back from payment page.
    """
    order_id = body.order_id

    # Fetch order status from Cashfree
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(
            f"{_cashfree_base_url()}/orders/{order_id}",
            headers=_cashfree_headers(),
        )

    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Could not verify payment with Cashfree")

    cf_order = resp.json()
    cf_status = cf_order.get("order_status", "").upper()

    # Find our transaction record
    async with db.execute(
        """SELECT * FROM transactions
           WHERE payment_ref = ? AND user_id = ?""",
        (order_id, current_user["id"]),
    ) as cursor:
        txn = await cursor.fetchone()

    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    if txn["status"] == "paid":
        return {
            "success": True,
            "already_credited": True,
            "message": "Credits already added to your account.",
        }

    if cf_status != "PAID":
        return {
            "success": False,
            "status": cf_status,
            "message": f"Payment not completed. Status: {cf_status}",
        }

    # Payment confirmed — credit the user
    await _credit_user(db, current_user["id"], txn["id"], txn["credits"])

    async with db.execute(
        "SELECT credits FROM users WHERE id = ?", (current_user["id"],)
    ) as cursor:
        row = await cursor.fetchone()

    return {
        "success": True,
        "credits_added": txn["credits"],
        "total_credits": row["credits"],
        "message": f"Payment successful! {txn['credits']} credit(s) added.",
    }


@router.post("/webhook")
async def cashfree_webhook(request: Request, db=Depends(get_db)):
    """
    Cashfree webhook — auto-credit user when payment succeeds.
    Cashfree POSTs here automatically after payment.
    Add this URL in Cashfree dashboard → Webhooks.
    """
    # Verify webhook signature
    payload = await request.body()
    cf_signature = request.headers.get("x-webhook-signature", "")
    cf_timestamp = request.headers.get("x-webhook-timestamp", "")

    if settings.CASHFREE_SECRET_KEY and cf_signature:
        msg = f"{cf_timestamp}{payload.decode()}"
        expected = hmac.new(
            settings.CASHFREE_SECRET_KEY.encode(),
            msg.encode(),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected, cf_signature):
            raise HTTPException(status_code=400, detail="Invalid webhook signature")

    import json
    data = json.loads(payload)
    event_type = data.get("type", "")

    if event_type != "PAYMENT_SUCCESS_WEBHOOK":
        return {"received": True}  # Ignore non-payment events

    order_id = data.get("data", {}).get("order", {}).get("order_id", "")
    if not order_id:
        return {"received": True}

    # Find transaction
    async with db.execute(
        "SELECT * FROM transactions WHERE payment_ref = ? AND status = 'pending'",
        (order_id,),
    ) as cursor:
        txn = await cursor.fetchone()

    if txn:
        await _credit_user(db, txn["user_id"], txn["id"], txn["credits"])

    return {"received": True}


async def _credit_user(db, user_id: str, txn_id: str, credits: int):
    """Internal helper: add credits and mark transaction as paid."""
    await db.execute(
        "UPDATE users SET credits = credits + ? WHERE id = ?",
        (credits, user_id),
    )
    await db.execute(
        "UPDATE transactions SET status = 'paid' WHERE id = ?",
        (txn_id,),
    )
    await db.commit()


@router.get("/transactions")
async def get_transactions(
    current_user: dict = Depends(require_auth),
    db=Depends(get_db),
):
    """User's transaction history."""
    async with db.execute(
        """SELECT id, amount_paise, credits, status, created_at
           FROM transactions WHERE user_id = ?
           ORDER BY created_at DESC LIMIT 20""",
        (current_user["id"],),
    ) as cursor:
        rows = await cursor.fetchall()

    return {
        "transactions": [
            {**dict(r), "amount_rupees": r["amount_paise"] / 100}
            for r in rows
        ]
    }
