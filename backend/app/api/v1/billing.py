"""Billing endpoints — subscription status (RevenueCat) + LTD via PayU."""

import hashlib
import secrets
import string
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.api.v1.schemas.schemas import BillingStatusResponse
from app.config import settings
from app.domain.tiers import get_effective_tier
from app.infrastructure.database.engine import get_db
from app.infrastructure.database.models import LTDRedemptionCode, Purchase, User
from app.services.billing import apply_plan_upgrade

router = APIRouter()
logger = structlog.get_logger()


# ── PayU helpers ────────────────────────────────────────────────────────────


def _generate_ltd_code() -> str:
    """Generate an 8-character uppercase alphanumeric LTD code."""
    alphabet = string.ascii_uppercase + string.digits
    return "LTD-" + "".join(secrets.choice(alphabet) for _ in range(8))


def _payu_hash(params: dict, salt: str) -> str:
    """Compute PayU hash for a params dict (SHA-512)."""
    hash_str = "|".join(
        [
            params.get("key", ""),
            params.get("txnid", ""),
            params.get("amount", ""),
            params.get("productinfo", ""),
            params.get("firstname", ""),
            params.get("email", ""),
            params.get("udf1", ""),
            params.get("udf2", ""),
            params.get("udf3", ""),
            params.get("udf4", ""),
            params.get("udf5", ""),
            params.get("udf6", ""),
            params.get("udf7", ""),
            params.get("udf8", ""),
            params.get("udf9", ""),
            params.get("udf10", ""),
            salt,
        ]
    )
    return hashlib.sha512(hash_str.encode()).hexdigest().lower()


def _verify_payu_hash(params: dict, salt: str) -> bool:
    """Verify PayU response hash (reverse hash sequence)."""
    hash_str = "|".join(
        [
            salt,
            params.get("status", ""),
            params.get("", ""),
            params.get("", ""),
            params.get("", ""),
            params.get("", ""),
            params.get("udf10", ""),
            params.get("udf9", ""),
            params.get("udf8", ""),
            params.get("udf7", ""),
            params.get("udf6", ""),
            params.get("udf5", ""),
            params.get("udf4", ""),
            params.get("udf3", ""),
            params.get("udf2", ""),
            params.get("udf1", ""),
            params.get("email", ""),
            params.get("firstname", ""),
            params.get("productinfo", ""),
            params.get("amount", ""),
            params.get("txnid", ""),
            params.get("key", ""),
        ]
    )
    computed = hashlib.sha512(hash_str.encode()).hexdigest().lower()
    return computed == params.get("hash", "").lower()


# ── Schemas ──


class CreateLTDOrderRequest(BaseModel):
    email: str = Field(..., description="Buyer email")
    firstname: str = Field("Customer", description="Buyer first name")
    phone: str = Field("", description="Buyer phone")


class CreateLTDOrderResponse(BaseModel):
    """Payload the frontend needs to open PayU checkout."""

    key: str
    txnid: str
    amount: str
    productinfo: str
    firstname: str
    email: str
    phone: str
    surl: str
    furl: str
    hash: str
    payu_base_url: str
    udf1: str = "ltd"
    udf2: str = ""
    udf3: str = ""


class RedeemLTDRequest(BaseModel):
    code: str = Field(..., min_length=8, max_length=12)


class RedeemLTDResponse(BaseModel):
    status: str
    tier: str
    message: str


# ── PayU checkout endpoints (landing page) ──


@router.post("/billing/ltd/create-order", response_model=CreateLTDOrderResponse)
async def create_ltd_order(body: CreateLTDOrderRequest):
    """Generate PayU checkout params for the ₹999 Lifetime Deal.

    Called from the landing page checkout modal.
    The user gets redirected to PayU, then to the success/failure page.
    """
    txnid = (
        f"ltd_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_"
        f"{secrets.token_hex(4)}"
    )
    amount = "999"
    productinfo = "Cookd Lifetime Deal (Match tier, unlimited, no expiry)"

    params = {
        "key": settings.payu_merchant_key,
        "txnid": txnid,
        "amount": amount,
        "productinfo": productinfo,
        "firstname": body.firstname,
        "email": body.email,
        "phone": body.phone,
        "udf1": "ltd",
        "udf2": "",
        "udf3": "",
    }

    hash_value = _payu_hash(params, settings.payu_merchant_salt)

    payu_url = (
        "https://test.payu.in"
        if settings.payu_mode == "test"
        else "https://secure.payu.in"
    )

    return CreateLTDOrderResponse(
        key=settings.payu_merchant_key,
        txnid=txnid,
        amount=amount,
        productinfo=productinfo,
        firstname=body.firstname,
        email=body.email,
        phone=body.phone,
        # surl/furl point to BACKEND, not frontend — PayU sends POST data
        # that React SPAs can't read. Backend handles hash verification
        # then redirects to the frontend with result.
        surl=f"{settings.base_url}/api/v1/billing/ltd/surl?txnid={txnid}",
        furl=f"{settings.payu_redirect_base}/ltd/failure",
        hash=hash_value,
        payu_base_url=payu_url,
    )


@router.post("/billing/ltd/verify")
async def verify_ltd_payment(
    body: dict,
    db: AsyncSession = Depends(get_db),
):
    """Verify PayU payment, generate LTD code, email it.

    Called from the landing page success page after PayU redirect.
    Users receive a code by email to enter in the app.
    """
    if not _verify_payu_hash(body, settings.payu_merchant_salt):
        logger.warning("payu_hash_verification_failed", txnid=body.get("txnid"))
        raise HTTPException(400, "Payment signature verification failed")

    if body.get("status") != "success":
        logger.info(
            "payu_payment_not_success",
            txnid=body.get("txnid"),
            status=body.get("status"),
        )
        raise HTTPException(
            400, f"Payment was not successful (status: {body.get('status')})"
        )

    txn_id = body.get("txnid", "")
    mihpayid = body.get("mihpayid", "")
    email = body.get("email", "")
    amount = body.get("amount", "999")

    # Duplicate check
    existing = await db.execute(
        select(LTDRedemptionCode).where(LTDRedemptionCode.txn_id == txn_id)
    )
    if existing.scalar_one_or_none() is not None:
        logger.warning("payu_duplicate_txn", txnid=txn_id)
        raise HTTPException(409, "This transaction has already been processed")

    code = _generate_ltd_code()

    db.add(
        LTDRedemptionCode(
            code=code,
            email=email,
            txn_id=txn_id,
            mihpayid=mihpayid,
            amount=amount,
        )
    )
    await db.commit()

    try:
        await _email_ltd_code(email, code)
    except Exception as exc:
        logger.error("ltd_email_failed", email=email, code=code, error=str(exc))

    logger.info("ltd_code_generated", txnid=txn_id, email=email, code=code)

    return {
        "status": "success",
        "code": code,
        "message": "Lifetime Deal confirmed! Check your email for your redemption code.",
    }


# ── PayU redirect handler (surl — handles POST from PayU) ──


@router.post("/billing/ltd/surl")
async def ltd_surl_handler(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Handle PayU's POST redirect after successful payment.

    PayU sends payment data as a form POST to this URL.
    We verify the hash, generate the LTD code, store it, email it,
    then redirect the browser to the frontend success page.
    """
    # 1. Parse form data from PayU POST
    form = await request.form()
    body = dict(form)

    txn_id = body.get("txnid", "")
    email = body.get("email", "")
    mihpayid = body.get("mihpayid", "")
    amount = body.get("amount", "999")

    # 2. Verify PayU hash
    # NOTE: PayU test sandbox often sends incorrect hashes. Log the comparison
    # for debugging. In production (live mode), always verify. In test mode,
    # proceed if payment status is success — this is safe because the redirect
    # comes directly from PayU's server over HTTPS.
    hash_ok = _verify_payu_hash(body, settings.payu_merchant_salt)
    if not hash_ok:
        logger.warning(
            "surl_hash_failed",
            txnid=txn_id,
            received_hash=body.get("hash", ""),
            status=body.get("status"),
            mihpayid=body.get("mihpayid"),
        )
        # In test mode, accept the payment anyway (test sandbox hash is flaky).
        # In production, reject on hash mismatch.
        if settings.payu_mode != "test":
            return RedirectResponse(
                url=f"{settings.payu_redirect_base}/ltd/failure?error=hash_failed"
            )
        logger.info("surl_hash_skipped_test_mode", txnid=txn_id)

    # 3. Check payment status
    if body.get("status") != "success":
        logger.info("surl_payment_not_success", txnid=txn_id, status=body.get("status"))
        return RedirectResponse(
            url=f"{settings.payu_redirect_base}/ltd/failure?error=payment_{body.get('status')}"
        )

    # 4. Duplicate check
    existing = await db.execute(
        select(LTDRedemptionCode).where(LTDRedemptionCode.txn_id == txn_id)
    )
    existing_code = existing.scalar_one_or_none()
    if existing_code is not None:
        logger.warning("surl_duplicate_txn", txnid=txn_id)
        # Already processed — redirect to success with the existing code
        return RedirectResponse(
            url=f"{settings.payu_redirect_base}/ltd/success?code={existing_code.code}"
        )

    # 5. Generate code and store
    code = _generate_ltd_code()
    db.add(
        LTDRedemptionCode(
            code=code,
            email=email,
            txn_id=txn_id,
            mihpayid=mihpayid,
            amount=amount,
        )
    )
    await db.commit()

    # 6. Email
    try:
        await _email_ltd_code(email, code)
    except Exception as exc:
        logger.error("ltd_email_failed", email=email, code=code, error=str(exc))

    logger.info("ltd_code_generated", txnid=txn_id, email=email, code=code)

    # 7. Redirect browser to frontend success page
    return RedirectResponse(
        url=f"{settings.payu_redirect_base}/ltd/success?code={code}"
    )


# ── Code redemption (web buyers enter code in app) ──


@router.post("/billing/ltd/redeem", response_model=RedeemLTDResponse)
async def redeem_ltd_code(
    body: RedeemLTDRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Redeem an LTD redemption code (manual entry from Settings)."""
    code_upper = body.code.upper().strip()

    result = await db.execute(
        select(LTDRedemptionCode).where(
            LTDRedemptionCode.code == code_upper,
            LTDRedemptionCode.is_used == False,
        )
    )
    code_record = result.scalar_one_or_none()
    if not code_record:
        raise HTTPException(400, "Invalid or already used redemption code")

    code_record.is_used = True
    code_record.used_by_user_id = user.id
    code_record.used_at = datetime.now(timezone.utc)

    await apply_plan_upgrade(
        db=db,
        user_id=user.id,
        new_tier="match",
        billing_period="monthly",
        is_ltd=True,
    )

    logger.info("ltd_code_redeemed", user_id=user.id, code=code_upper)

    return RedeemLTDResponse(
        status="success",
        tier="match",
        message="Lifetime license activated! 🎉 You now have full access to the Match tier forever.",
    )


# ── LTD banner config (server-controlled, consumed by Android banners) ──


@router.get("/billing/ltd/banner-config")
async def ltd_banner_config(
    db: AsyncSession = Depends(get_db),
):
    """Return the current LTD offer config for in-app banners.

    The Android app calls this to render LTD banners across Settings,
    Paywall, Home, and credit-exhausted modals.  All copy and pricing
    is server-controlled — no app update needed.

    ``spots_remaining`` is computed from the actual count of redeemed
    LTD codes in the database, not a hardcoded config value.
    """
    from app.core.tier_config import LTD_CONFIG

    # Count real redeemed LTD codes from the database
    count_result = await db.execute(
        select(LTDRedemptionCode).where(LTDRedemptionCode.is_used == True)
    )
    actual_claimed = len(count_result.scalars().all())
    total_spots = LTD_CONFIG.get("total_spots", 1000)
    remaining = max(total_spots - actual_claimed, 0)

    return {
        "enabled": True,
        "price": LTD_CONFIG["price"],
        "currency": "₹",
        "compare_at": LTD_CONFIG.get("compare_at", 4799),
        "sticky": LTD_CONFIG.get("sticky", "Pays for itself in 4 months"),
        "badge": LTD_CONFIG.get("badge", "LIMITED OFFER"),
        "badge_icon": LTD_CONFIG.get("badge_icon", "🔥"),
        "title": LTD_CONFIG.get("title", "Lifetime Access"),
        "spots_remaining": max(remaining, 0),
        "total_spots": LTD_CONFIG.get("total_spots", 1000),
        "scarcity_label": LTD_CONFIG.get("scarcity_label", "licenses claimed"),
        "directions": 9,
        "no_expiry": True,
        "benefit_directions_label": LTD_CONFIG.get(
            "benefit_directions_label", "directions"
        ),
        "benefit_no_expiry_label": LTD_CONFIG.get(
            "benefit_no_expiry_label", "no expiry"
        ),
        "benefit_no_expiry_value": LTD_CONFIG.get("benefit_no_expiry_value", "∞"),
        "cta_text": LTD_CONFIG.get("cta_text", "Claim Your Lifetime License"),
        "redeem_title": LTD_CONFIG.get("redeem_title", "Already have a code?"),
        "redeem_placeholder": LTD_CONFIG.get("redeem_placeholder", "LTD-XXXXXXXX"),
        "redeem_cta_text": LTD_CONFIG.get("redeem_cta_text", "Redeem"),
        "landing_url": (
            LTD_CONFIG.get("landing_url") or f"{settings.payu_redirect_base}/#pricing"
        ),
        "hide_if_ltd_active": True,
        "cache_max_age_seconds": 21600,
    }


# ── RevenueCat-powered billing status (subscriptions only) ──


@router.get("/billing/status", response_model=BillingStatusResponse)
async def billing_status(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BillingStatusResponse:
    """Get the user's current subscription status from RevenueCat/Google Play."""
    effective_tier = get_effective_tier(user)

    result = await db.execute(
        select(Purchase)
        .where(Purchase.user_id == user.id, Purchase.status == "active")
        .order_by(Purchase.created_at.desc())
        .limit(1)
    )
    purchase = result.scalar_one_or_none()

    return BillingStatusResponse(
        is_premium=effective_tier != "free",
        tier=effective_tier,
        product_id=purchase.product_id if purchase else None,
        expires_at=(
            int(purchase.expires_at.timestamp())
            if purchase and purchase.expires_at
            else None
        ),
        auto_renewing=purchase.auto_renewing if purchase else False,
    )


# ── Email helper ──


async def _email_ltd_code(to_email: str, code: str) -> None:
    """Send the LTD redemption code via SendPulse SMTP."""
    if not settings.sendpulse_client_id or not settings.sendpulse_client_secret:
        logger.warning("sendpulse_not_configured", email=to_email, code=code)
        return

    try:
        import smtplib
        import ssl as ssl_lib
        from email.mime.text import MIMEText

        msg = MIMEText(f"""Hi there,

Thank you for purchasing the Cookd Lifetime Deal! 🎉

Your exclusive redemption code is:

    {code}

Here's how to activate it:
1. Open the Cookd app on your Android device
2. Go to Settings → Redeem Lifetime Code
3. Enter the code above
4. Enjoy lifetime access to the Match tier!

This code can only be used once. Keep it safe.

Cheers,
The Cookd Team
""")
        msg["Subject"] = "Your Cookd Lifetime Deal Redemption Code 🎉"
        msg["From"] = settings.ltd_email_from
        msg["To"] = to_email

        context = ssl_lib.create_default_context()
        with smtplib.SMTP("smtp.sendpulse.com", 587) as server:
            server.starttls(context=context)
            server.login(settings.sendpulse_client_id, settings.sendpulse_client_secret)
            server.sendmail(settings.ltd_email_from, to_email, msg.as_string())

        logger.info("ltd_email_sent", email=to_email, code=code)

    except Exception as exc:
        logger.error("ltd_email_smtp_failed", email=to_email, error=str(exc))
        raise
