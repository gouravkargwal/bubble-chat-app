# Production flavor – required config

Production builds need **Firebase**, **Google Play**, and **RevenueCat** set up separately from staging. Full step-by-step is in the project root:

**→ [PRODUCTION_AND_STAGING_AUDIT.md](../../PRODUCTION_AND_STAGING_AUDIT.md)** (sections 5 Google Play, 6 RevenueCat, 7 next steps)

This file covers only what lives in **`app/src/production/`**.

---

## google-services.json (required in this folder)

1. Create a **separate Firebase project** for production (e.g. `cookd-prod`).
2. In that project, add an **Android app** with package name: **`com.cookd.app`** (no `.stg`).
3. Add your **production** app signing SHA-1(s) from **Play Console** (upload key + App signing key) in Firebase → Project settings → Your apps. See audit **§5 Google Play** for how to get them.
4. Download **google-services.json** from that production Firebase project.
5. Place it here: **`app/src/production/google-services.json`**.

Do **not** copy `app/src/staging/google-services.json` here – it is for package `com.cookd.app.stg` only.

Without this file, production builds may fail or Firebase (Auth, Crashlytics, etc.) will not work.

---

## Google Play & RevenueCat

- **Google Play:** Create app `com.cookd.app` in Play Console, enable Play App Signing, get SHA-1(s) and use them in Firebase/OAuth. See **PRODUCTION_AND_STAGING_AUDIT.md §5**.
- **RevenueCat:** Create production app in RevenueCat, link Google Play (service account), get Public API key, set **`REVENUE_CAT_PUBLIC_KEY_PROD`** in `local.properties` or `gradle.properties`. See **PRODUCTION_AND_STAGING_AUDIT.md §6**.
