# Implementation Plan: Referral System + Google Play Billing

## Overview
Two features shipping together:
1. **Referral System** — Users share codes, both sides get +5 bonus replies (cap: 10 referrals = 50 bonus max)
2. **Google Play Billing** — Two subscription tiers via Google Play Billing Library, server-side receipt verification

---

## PHASE 1: Referral System

### Backend Changes

#### 1A. Database — New columns on `users` + new `referrals` table
**File:** `backend/app/infrastructure/database/models.py`

Add to `User` model:
```python
referral_code: Mapped[str] = mapped_column(String(8), unique=True, index=True)
bonus_replies: Mapped[int] = mapped_column(Integer, default=0)
referred_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
```

New model:
```python
class Referral(Base):
    __tablename__ = "referrals"
    id: str (PK, uuid)
    referrer_id: str (FK users.id)
    referee_id: str (FK users.id)
    bonus_granted: int (default 5)
    created_at: datetime
```

#### 1B. Alembic Migration
**New file:** `backend/alembic/versions/xxxx_add_referral_system.py`
- Add `referral_code`, `bonus_replies`, `referred_by` columns to `users`
- Create `referrals` table
- Generate unique 8-char referral codes for existing users

#### 1C. Auto-generate referral code on user creation
**File:** `backend/app/api/v1/auth.py`
- When creating a new user, generate a random 8-char alphanumeric referral code
- Use helper function with retry on collision

#### 1D. New API routes — `/api/v1/referral/`
**New file:** `backend/app/api/v1/referral.py`

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/referral/me` | Get my referral code + stats (total referrals, bonus replies earned) |
| POST | `/referral/apply` | Apply a referral code (body: `{code: "ABC123"}`) |

**Apply logic:**
- Validate code exists and isn't the user's own
- Check user hasn't already been referred (`referred_by` is null)
- Check referrer hasn't exceeded 10 referrals cap
- Grant +5 bonus replies to both referrer and referee
- Create `Referral` record

#### 1E. Update quota logic to include bonus replies
**File:** `backend/app/api/v1/vision.py` (line 44)

Change rate check from:
```python
if not user.is_premium and daily_used >= user.daily_limit:
```
To:
```python
effective_limit = user.daily_limit + user.bonus_replies
if not user.is_premium and daily_used >= effective_limit:
```

**File:** `backend/app/api/v1/usage.py`
- Add `bonus_replies` to `UsageResponse` schema
- Return `effective_limit = daily_limit + bonus_replies`

#### 1F. Update schemas
**File:** `backend/app/api/v1/schemas/schemas.py`
- Add `ReferralInfoResponse(code, total_referrals, bonus_replies_earned, max_referrals)`
- Add `ApplyReferralRequest(code: str)`
- Add `ApplyReferralResponse(bonus_granted: int, new_total_bonus: int)`
- Update `UsageResponse` to add `bonus_replies: int`

#### 1G. Register referral router
**File:** `backend/app/api/v1/router.py`
- Import and include `referral_router`

---

### Android Changes

#### 1H. New DTOs
**File:** `RizzBotV2/.../data/remote/dto/HostedDtos.kt`
- Add `ReferralInfoResponse`, `ApplyReferralRequest`, `ApplyReferralResponse`
- Update `UsageResponse` to include `bonusReplies`

#### 1I. New API endpoints
**File:** `RizzBotV2/.../data/remote/api/HostedApi.kt`
- `GET api/v1/referral/me` → `ReferralInfoResponse`
- `POST api/v1/referral/apply` → `ApplyReferralResponse`

#### 1J. Repository layer
**File:** `RizzBotV2/.../data/repository/HostedRepositoryImpl.kt`
- Add `getReferralInfo()` and `applyReferralCode(code)` methods
- Update `UsageState` to include `bonusReplies`

**File:** `RizzBotV2/.../domain/repository/HostedRepository.kt`
- Add interface methods

**File:** `RizzBotV2/.../domain/model/UsageState` (in HostedMode.kt)
- Add `bonusReplies: Int = 0` field
- Update `dailyRemaining` to factor in bonus

#### 1K. Referral UI in Settings screen
**File:** `RizzBotV2/.../ui/settings/SettingsScreen.kt`
- Add "Invite Friends" card showing referral code + share button
- Add "Enter Referral Code" input field
- Show referral stats (X friends invited, Y bonus replies)

**File:** `RizzBotV2/.../ui/settings/SettingsViewModel.kt`
- Add referral state, share action, apply code action

---

## PHASE 2: Google Play Billing

### Android Changes (Primary — billing happens client-side)

#### 2A. Add Billing dependency
**File:** `RizzBotV2/app/build.gradle.kts`
```kotlin
implementation("com.android.billingclient:billing-ktx:7.1.1")
```

#### 2B. BillingManager singleton
**New file:** `RizzBotV2/.../data/billing/BillingManager.kt`

Responsibilities:
- Connect to Google Play Billing service
- Query available subscriptions (product IDs: `cookd_premium_monthly`, `cookd_pro_monthly`)
- Launch purchase flow
- Handle purchase result (acknowledge + verify with backend)
- Restore purchases on app start

Key methods:
```kotlin
fun connect()
fun queryProducts(): List<ProductDetails>
fun launchPurchase(activity: Activity, productDetails: ProductDetails)
fun handlePurchaseResult(purchase: Purchase)  // → calls backend verify
fun disconnect()
```

#### 2C. New backend API endpoints for purchase verification
**New file:** `backend/app/api/v1/billing.py`

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/billing/verify` | Verify Google Play purchase receipt |
| POST | `/billing/webhook` | Google Play RTDN (real-time developer notifications) |
| GET | `/billing/status` | Get current subscription status |

**Verify flow:**
1. App sends `purchase_token` + `product_id` to backend
2. Backend calls Google Play Developer API to validate receipt
3. If valid → set `is_premium = True`, `premium_expires_at` = subscription end date
4. Acknowledge the purchase server-side

**Webhook flow (RTDN):**
- Google sends notifications on subscription changes (renewal, cancel, pause)
- Backend updates user's premium status accordingly

#### 2D. Google Play Developer API client
**New file:** `backend/app/infrastructure/billing/google_play.py`

- Uses `google-auth` + `httpx` to call `androidpublisher.googleapis.com`
- Verifies subscription purchase tokens
- Gets subscription status (active, cancelled, expired)
- Needs Google Play service account credentials (separate from Firebase)

#### 2E. New backend dependency
**File:** `backend/pyproject.toml`
- Add `google-auth>=2.0` (for Google Play API auth)

#### 2F. Backend config additions
**File:** `backend/app/config.py`
```python
google_play_service_account: str = ""  # path to service account JSON
google_play_package_name: str = "com.cookd.app"
```

#### 2G. New DB model for purchase history
**File:** `backend/app/infrastructure/database/models.py`

```python
class Purchase(Base):
    __tablename__ = "purchases"
    id: str (PK, uuid)
    user_id: str (FK users.id)
    product_id: str  # "cookd_premium_monthly" or "cookd_pro_monthly"
    purchase_token: str (unique)
    status: str  # "active", "cancelled", "expired", "refunded"
    started_at: datetime
    expires_at: datetime
    created_at: datetime
```

#### 2H. Alembic migration for purchases
**New file:** `backend/alembic/versions/xxxx_add_purchases_table.py`

#### 2I. Update PremiumScreen with real billing
**File:** `RizzBotV2/.../ui/premium/PremiumScreen.kt`
- Replace "COMING SOON" with actual purchase buttons
- Show real prices from Google Play (localized per country automatically)
- Handle purchase flow: button tap → BillingManager.launchPurchase() → verify with backend → update UI
- Show current subscription status if already premium

#### 2J. PremiumViewModel
**New file:** `RizzBotV2/.../ui/premium/PremiumViewModel.kt`
- Query available products on init
- Handle purchase callbacks
- Verify with backend after successful purchase
- Expose subscription state

#### 2K. DI module for billing
**File:** `RizzBotV2/.../di/AppModule.kt`
- Provide BillingManager singleton

#### 2L. Register billing router
**File:** `backend/app/api/v1/router.py`
- Import and include `billing_router`

#### 2M. Backend billing schemas
**File:** `backend/app/api/v1/schemas/schemas.py`
- `VerifyPurchaseRequest(purchase_token, product_id, order_id)`
- `VerifyPurchaseResponse(is_valid, premium_until)`
- `BillingStatusResponse(is_premium, product_id, expires_at, auto_renewing)`

---

## Implementation Order

| Step | Task | Effort |
|------|------|--------|
| 1 | Backend: Referral DB model + migration | Small |
| 2 | Backend: Referral API routes + apply logic | Medium |
| 3 | Backend: Update quota to include bonus replies | Small |
| 4 | Android: Referral DTOs + API + repository | Small |
| 5 | Android: Referral UI in Settings | Medium |
| 6 | Backend: Purchase DB model + migration | Small |
| 7 | Backend: Google Play verification client | Medium |
| 8 | Backend: Billing API routes (verify, webhook, status) | Medium |
| 9 | Android: Add billing library + BillingManager | Medium |
| 10 | Android: PremiumViewModel + update PremiumScreen | Medium |
| 11 | Android: Wire billing into DI + restore on app start | Small |

**Total: ~11 steps, starting with referral (simpler) then billing.**

---

## Product IDs for Google Play Console
- `cookd_premium_monthly` — $4.99/mo (Premium tier)
- `cookd_pro_monthly` — $9.99/mo (Pro tier)

These need to be created in Google Play Console > Monetization > Subscriptions before the billing code can query them. Country-specific pricing is set there too (e.g., ₹149/mo for India for Premium).

## Files Created/Modified Summary

### New Files (7)
1. `backend/app/api/v1/referral.py`
2. `backend/app/api/v1/billing.py`
3. `backend/app/infrastructure/billing/google_play.py`
4. `backend/alembic/versions/xxxx_add_referral_system.py`
5. `backend/alembic/versions/xxxx_add_purchases_table.py`
6. `RizzBotV2/.../data/billing/BillingManager.kt`
7. `RizzBotV2/.../ui/premium/PremiumViewModel.kt`

### Modified Files (14)
1. `backend/app/infrastructure/database/models.py` — Add Referral, Purchase models + User fields
2. `backend/app/api/v1/schemas/schemas.py` — Add referral + billing schemas
3. `backend/app/api/v1/router.py` — Register new routers
4. `backend/app/api/v1/auth.py` — Generate referral code on user creation
5. `backend/app/api/v1/vision.py` — Include bonus_replies in quota check
6. `backend/app/api/v1/usage.py` — Return bonus_replies in response
7. `backend/app/config.py` — Add Google Play config
8. `backend/pyproject.toml` — Add google-auth dependency
9. `RizzBotV2/app/build.gradle.kts` — Add billing dependency
10. `RizzBotV2/.../data/remote/dto/HostedDtos.kt` — Add referral + billing DTOs
11. `RizzBotV2/.../data/remote/api/HostedApi.kt` — Add referral + billing endpoints
12. `RizzBotV2/.../data/repository/HostedRepositoryImpl.kt` — Add referral + billing methods
13. `RizzBotV2/.../ui/settings/SettingsScreen.kt` — Add referral UI
14. `RizzBotV2/.../ui/premium/PremiumScreen.kt` — Replace coming soon with real billing
