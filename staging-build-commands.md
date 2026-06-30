# RizzBot / Cookd – Build, Install & Run Commands

## Android (RizzBotV2)

### Prerequisites

- Android device or emulator connected (`adb devices`)
- Java JDK installed and configured
- Project root: `RizzBotV2/`

---

### Staging Debug Build

```bash
cd /Users/gouravkargwal/bubble-chat-app/RizzBotV2
./gradlew assembleStagingDebug
adb install -r app/build/outputs/apk/staging/debug/app-staging-debug.apk
```

---

### Staging Release Build (signed)

```bash
cd /Users/gouravkargwal/bubble-chat-app/RizzBotV2
./gradlew assembleStagingRelease
adb install -r app/build/outputs/apk/staging/release/app-staging-release.apk
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

- **Application ID:** `com.cookd.mobile.stg`
- **App Name:** `Cookd (Staging)`
- **APK Location:** `app/build/outputs/apk/staging/<buildType>/`

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

| Service   | URL                      |
|-----------|--------------------------|
| API       | `http://localhost:8000`  |
| Grafana   | `http://localhost:3333`  |
| Loki      | `http://localhost:3110`  |
| Postgres  | `localhost:5432` (user: `cookd`, pass: `cookd`) |

---

## Backend – Audio/Video Factory Script

```bash
cd /Users/gouravkargwal/bubble-chat-app/backend

ENV_FILE=".env.stage" python -m scripts.audio_video_factory
```
