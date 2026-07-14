# RizzBot / Cookd – Build & Release Commands

## Android (RizzBotV2)

### Prerequisites

- Android device or emulator connected (`adb devices`)
- Java JDK installed and configured
- Project root: `RizzBotV2/`

---

### Staging Debug Build

```bash
./gradlew assembleStagingDebug
adb install -r app/build/outputs/apk/staging/debug/app-staging-debug.apk
```

---

### Staging Release Build (signed)

```bash
./gradlew assembleStagingRelease
adb install -r app/build/outputs/apk/staging/release/app-staging-release.apk
```

---

### Production Release AAB (for Google Play)

```bash
# Clean previous builds
./gradlew clean

# Build production release AAB
./gradlew bundleProductionRelease

# Output: app/build/outputs/bundle/productionRelease/app-production-release.aab
```

---

### Production Release APK (for local testing)

```bash
cd /Users/gouravkargwal/bubble-chat-app/RizzBotV2
./gradlew assembleProductionRelease
adb install -r app/build/outputs/apk/production/release/app-production-release.apk
```

---

### Build All Release Variants

```bash
cd /Users/gouravkargwal/bubble-chat-app/RizzBotV2
./gradlew assembleStagingRelease assembleProductionRelease
```

---

### Useful ADB Commands

```bash
# Check connected devices
adb devices

# Uninstall staging app (if signature conflict)
adb uninstall com.cookd.mobile.stg

# Find generated APKs
find app/build/outputs -name "*.apk" | grep staging
```

---

### App Details

| Variant    | Application ID         | App Name          |
| ---------- | ---------------------- | ----------------- |
| Staging    | `com.cookd.mobile.stg` | `Cookd (Staging)` |
| Production | `com.cookd.mobile`     | `Cookd`           |

### APK / AAB Locations

| Variant    | Build Type | Output Path                                                                                             |
| ---------- | ---------- | ------------------------------------------------------------------------------------------------------- |
| Staging    | Debug      | `app/build/outputs/apk/staging/debug/app-staging-debug.apk`                                             |
| Staging    | Release    | `app/build/outputs/apk/staging/release/app-staging-release.apk`                                         |
| Production | Release    | `app/build/outputs/bundle/productionRelease/app-production-release.aab` (run `bundleProductionRelease`) |
| Production | Release    | `app/build/outputs/apk/production/release/app-production-release.apk` (APK for local testing)           |

### Versioning

- **Current:** `versionCode = 29`, `versionName = "2.0.1"`
- **Location:** `app/build.gradle.kts` → `defaultConfig` block
- **Update:** Increment `versionCode` by 1 and bump `versionName` before each release

---

## Backend – Docker Commands

### Prerequisites

- Docker & Docker Compose installed
- Project root: `backend/`

---

### Development Stack (docker-compose.yml)

```bash
cd /Users/gouravkargwal/bubble-chat-app/backend

# Start all dev services (postgres, api, loki, promtail, grafana)
docker compose up -d --build

# Stop all dev services
docker compose down

# View logs
docker compose logs -f api

# Access database shell
docker compose exec postgres psql -U cookd
```

---

### Production Stack (docker-compose.prod.yml)

```bash
cd /Users/gouravkargwal/bubble-chat-app/backend

# Start production services
docker compose -f docker-compose.prod.yml up -d --build

# Stop production services
docker compose -f docker-compose.prod.yml down
```

---

### Makefile Shortcuts

```bash
cd /Users/gouravkargwal/bubble-chat-app/backend

make docker-dev        # same as docker compose up -d --build
make docker-prod       # same as docker compose -f docker-compose.prod.yml up -d --build
make docker-down       # same as docker compose down
make docker-down-prod  # same as docker compose -f docker-compose.prod.yml down
```

---

### Backend URLs

| Service  | URL                                             |
| -------- | ----------------------------------------------- |
| API      | `http://localhost:8000`                         |
| Grafana  | `http://localhost:3333`                         |
| Loki     | `http://localhost:3110`                         |
| Postgres | `localhost:5432` (user: `cookd`, pass: `cookd`) |

---

## Backend – Audio/Video Factory Script

```bash
cd /Users/gouravkargwal/bubble-chat-app/backend

ENV_FILE=".env.stage" python -m scripts.audio_video_factory


docker compose --env-file .env.dev up -d

```
