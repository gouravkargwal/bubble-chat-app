# Production vs Staging – Configuration Audit

## 1. Should production use a new Firebase/Google project?

**Yes. Use a separate Firebase (and Google Cloud) project for production.**

- **Staging** → current project `cookd-stage-490313` (project number 226210127602).
- **Production** → create a new project, e.g. `cookd-prod` or `cookd`, and use it only for production.

Benefits:
- No risk of mixing staging and production data (Auth, Firestore, etc.).
- Separate quotas, billing, and security.
- Production OAuth/SHA-1 config is independent of staging.
- Clear separation when debugging (staging = one project, prod = another).

---

## 2. App name and package – correct

| Item | Value | Notes |
|------|--------|------|
| **App name (main)** | `Cookd` | From `res/values/strings.xml` → `app_name`. |
| **Staging app name** | `Cookd (Staging)` | Overridden in `build.gradle.kts` via `resValue("string", "app_name", "Cookd (Staging)")`. |
| **Production app name** | `Cookd` | Uses main `strings.xml` (no override in production flavor). |
| **Production package** | `com.cookd.app` | `defaultConfig.applicationId`. |
| **Staging package** | `com.cookd.app.stg` | `applicationIdSuffix = ".stg"`. |
| **Manifest label** | `@string/app_name` | Resolves per flavor. |

No change needed for app name or package.

---

## 3. Misconfigurations found

### 3.1 Production has no Firebase config

- **`app/src/production/`** is empty – there is **no `google-services.json`** for production.
- **`app/src/staging/google-services.json`** exists and is for package `com.cookd.app.stg` only.

So production builds either:
- Fail if the Google Services plugin requires a file per variant, or  
- Use no Firebase config (or a wrong one), so Auth/Crashlytics/etc. are broken or undefined.

**Fix:** Create a **production Firebase project**, add an Android app with package `com.cookd.app`, download `google-services.json`, and place it in **`app/src/production/google-services.json`**.

---

### 3.2 Production has no Google Web Client ID

In `app/build.gradle.kts`:

- **Staging** sets:  
  `buildConfigField("String", "GOOGLE_WEB_CLIENT_ID", "\"226210127602-opgeg6...\"")`
- **Production** does **not** set `GOOGLE_WEB_CLIENT_ID`.

So production uses `defaultConfig`, which reads from **`gradle.properties`**:

```properties
GOOGLE_WEB_CLIENT_ID=901515523917-8aorui4u73e5k0uj5004vf9datbig05d.apps.googleusercontent.com
```

That value is for a **different** project (901515523917), not your staging project (226210127602). For production you must use the **production** Firebase/Google project’s Web client ID, not this one.

**Fix:** In the production flavor, set `GOOGLE_WEB_CLIENT_ID` explicitly (see suggested `build.gradle.kts` change below). Do **not** rely on `gradle.properties` for production.

---

### 3.3 RevenueCat production key is a placeholder

- **Staging:** `REVENUE_CAT_PUBLIC_KEY` = `goog_mvwllCzumJLbCSLXWVnFtqKIZqd` (set in build.gradle).
- **Production:** `REVENUE_CAT_PUBLIC_KEY` = `"REPLACE_WITH_PRODUCTION_KEY"`.

**Fix:** Replace with the real production RevenueCat API key (Google Play) before shipping production.

---

### 3.4 Backend URL

- **Staging:** `https://nonconscientious-annette-saddeningly.ngrok-free.dev/`
- **Production:** `https://api.cookd.app/`

These are correctly set per flavor and used via `BuildConfig.BACKEND_URL` in `NetworkModule`. No change needed.

---

### 3.5 Where BuildConfig is used

- `BuildConfig.BACKEND_URL` → `NetworkModule.provideHostedApi()` (Retrofit baseUrl). OK.
- `BuildConfig.GOOGLE_WEB_CLIENT_ID` → `GoogleSignInHelper`. Must be set per flavor (see above).
- `BuildConfig.REVENUE_CAT_PUBLIC_KEY` → `MainActivity` Purchases configuration. Must be set for production.

---

## 4. Summary checklist

| Config | Staging | Production |
|--------|---------|------------|
| Package | `com.cookd.app.stg` | `com.cookd.app` |
| App name | Cookd (Staging) | Cookd |
| `google-services.json` | ✅ `app/src/staging/` | ❌ Missing – add under `app/src/production/` |
| `GOOGLE_WEB_CLIENT_ID` | ✅ Set in build.gradle | ❌ Uses wrong value from gradle.properties – set in build.gradle from prod project |
| `REVENUE_CAT_PUBLIC_KEY` | ✅ Set | ❌ Placeholder – replace with prod key |
| `BACKEND_URL` | ✅ ngrok | ✅ api.cookd.app |

---

## 5. Google Play (Play Console) setup

Use this for the **production** app (`com.cookd.app`). Staging can use a separate app/track or the same console with a different package.

### 5.1 Create or use the production app in Play Console

1. Go to [Google Play Console](https://play.google.com/console).
2. Create a new app (or select existing) with **package name `com.cookd.app`**.
3. Complete required store listing, content rating, privacy policy, and target audience.

### 5.2 App signing (required for Google Sign-In / OAuth)

1. In Play Console: **Your app → Release → Setup → App integrity**.
2. Enable **Google Play App Signing** (recommended). Google will re-sign your AAB with the **App signing key**.
3. **Upload key:** Use your release keystore (e.g. `upload-keystore.jks` from `keystore.properties`). Upload the first AAB signed with this key; Play will accept it and re-sign for distribution.
4. **Get SHA-1 fingerprints:**
   - **Upload key SHA-1:** From your local keystore (e.g. `keytool -list -v -keystore app/upload-keystore.jks -alias upload-key`). You already have this (e.g. `8B:1D:...` for staging).
   - **App signing key SHA-1:** In Play Console → **App integrity → App signing** → copy the **App signing certificate** SHA-1 (Google manages this key).
5. Use **both** SHA-1 values in **Firebase** (production project) and in **Google Cloud** OAuth Android client for `com.cookd.app`, so sign-in works for:
   - Builds you install locally (upload key).
   - Builds installed from Play (internal/closed/production) (App signing key).

### 5.3 Internal / closed testing

1. **Release → Testing → Internal testing** (or Closed testing).
2. Create a release and upload the **production** AAB: `app/build/outputs/bundle/stagingRelease/` is for **staging**; for production use **`app/build/outputs/bundle/productionRelease/app-production-release.aab`**.
3. Add testers (email list or Google Group). Save and get the **opt-in link**.
4. Testers install from the link; the app will be signed with the **App signing key** – ensure that SHA-1 is in Firebase/OAuth (see above).

### 5.4 Summary – what to copy from Play Console

- **App signing certificate SHA-1** (and optionally upload key SHA-1) → add to **Firebase** (production Android app) and to **Google Cloud** OAuth 2.0 Android client for `com.cookd.app`.
- Use the **same** production Firebase project and Web client ID in the app’s `GOOGLE_WEB_CLIENT_ID_PROD` / BuildConfig.

---

## 6. RevenueCat setup

Use a **separate RevenueCat project or app** for production so staging and production data are not mixed.

### 6.1 Create production app in RevenueCat

1. Go to [RevenueCat](https://app.revenuecat.com).
2. Use an existing project or create one (e.g. “Cookd”).
3. **Apps:** Add an app (or use existing) – e.g. **“Cookd Android Production”**.
4. **Platform:** Google Play Store.
5. **Package name:** `com.cookd.app` (must match your production `applicationId`).

### 6.2 Link Google Play to RevenueCat

1. In RevenueCat → **Your app → Project Settings → Service credentials** (or **Google Play** integration).
2. Create a **Google Play service account** (or use existing):
   - In [Google Cloud Console](https://console.cloud.google.com) (use your **production** Firebase/Google project or a project with Play API access), go to **IAM & Admin → Service accounts**.
   - Create a service account, create a JSON key, and download it.
   - In **Google Play Console → Setup → API access**, link this service account and grant it **at least** “View app information and download bulk reports” (and any permission RevenueCat asks for, e.g. “View financial data” for subscriptions).
3. In RevenueCat, upload the **JSON key** or paste the credentials as instructed. Save.

### 6.3 Get the production API key

1. In RevenueCat → **Your app → API Keys**.
2. Ensure you have an **Android** key for the **production** app (Google Play).
3. Copy the **Public API key** (starts with `goog_` for Google Play). This is the key the app uses in `Purchases.configure(...)`.
4. Put it in the app via one of:
   - **`local.properties`** (recommended – not committed):  
     `REVENUE_CAT_PUBLIC_KEY_PROD=goog_xxxxxxxxxxxx`
   - Or **`gradle.properties`** (avoid committing if it’s in git):  
     `REVENUE_CAT_PUBLIC_KEY_PROD=goog_xxxxxxxxxxxx`
   - Production flavor in `build.gradle.kts` reads `REVENUE_CAT_PUBLIC_KEY_PROD` and passes it to BuildConfig.

### 6.4 Products / entitlements

1. In RevenueCat, define **Products** and **Entitlements** (e.g. “pro”, “premium”) and link them to your **Google Play** in-app products / subscriptions.
2. Ensure package name in RevenueCat matches **`com.cookd.app`** and that the same products exist in **Play Console → Monetize → Products**.

### 6.5 Summary – what to copy into the app

- **RevenueCat Public API key** (Google Play, production app) → set as **`REVENUE_CAT_PUBLIC_KEY_PROD`** in `local.properties` or `gradle.properties` so the production flavor gets the correct key at build time.

---

## 7. Recommended next steps (order)

1. **Google Play:** Create/use app `com.cookd.app` in Play Console, enable Play App Signing, get **App signing** (and upload) **SHA-1**.
2. **Firebase:** Create production Firebase project, add Android app `com.cookd.app`, add both SHA-1s, download **`google-services.json`** → **`app/src/production/google-services.json`**.
3. **Google Cloud (same project as Firebase):** Create OAuth 2.0 Web client + Android client for `com.cookd.app` with both SHA-1s; copy **Web client ID**.
4. **App config:** Set `GOOGLE_WEB_CLIENT_ID_PROD` and `REVENUE_CAT_PUBLIC_KEY_PROD` in `local.properties` (or gradle.properties).
5. **RevenueCat:** Create production app, link Google Play (service account), copy **Public API key** into `REVENUE_CAT_PUBLIC_KEY_PROD`.
6. Build **productionRelease**, upload AAB to **Internal testing**, install from Play and test **sign-in** and **purchases**.
