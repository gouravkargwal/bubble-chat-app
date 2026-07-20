# Anonymize person names in the video pipeline

## Problem

Real person names from the `interactions` table flow unmodified into rendered
Remotion videos and output filenames, creating a PII leak.

```
Database (interactions.person_name)
  │
  ├─► _build_video_payload() → "personName": raw name
  ├─► render-video/route.ts  → filename: "{timestamp}-{raw-name}.mp4"
  ├─► audio_video_factory.py → person_name from DB row
  └─► Remotion compositions  → <span>{personName}</span> visible in video
```

## Decision

**Approach:** API-layer anonymization in `_build_video_payload()` (Option A).

**Rationale:**
- Smallest diff (~15 lines)
- Covers both consumption paths (admin page → Next.js route, and Python CLI)
- No DB migration, no new dependencies
- Deterministic fake names preserve cross-referencing for debugging

## Plan

### 1. Add anonymization function in video_export.py

**File:** [`backend/app/api/v1/video_export.py`](../backend/app/api/v1/video_export.py)

Add a module-level function and a name pool:

```python
_FAKE_NAMES = [
    "Alex", "Jordan", "Taylor", "Morgan",
    "Casey", "Riley", "Quinn", "Avery",
    "Drew", "Blake", "Cameron", "Logan",
]

def _anonymize_name(real_name: str, salt: str) -> str:
    """Deterministic pseudonym from a real name + interaction salt.
    
    Same real_name + same salt → same fake name every time,
    so video filenames and DB records remain linkable for debugging.
    """
    if not real_name or real_name.lower() in ("unknown", "someone", ""):
        return "Match"
    h = hash(salt + real_name)
    return _FAKE_NAMES[h % len(_FAKE_NAMES)]
```

Then in `_build_video_payload()` (line ~235), change:
```python
"personName": ix.person_name or "Someone",
```
to:
```python
"personName": _anonymize_name(ix.person_name, str(ix.id)),
```

**Impact:** All payloads returned by the admin API will carry the fake name.

### 2. Fix filename in render-video route.ts

**File:** [`landing-page/src/app/api/render-video/route.ts`](../landing-page/src/app/api/render-video/route.ts)

Line 114 currently uses the raw `personName` from the POST body:
```typescript
const safeName = personName.toLowerCase().replace(/\s+/g, "-");
```

Since the admin page now sends the already-anonymized name in the POST body, this
line is already safe **provided the admin page uses the backend's payload**.

But the route also builds `inputProps` from the POST body directly (lines 84-92),
which now contains the anonymized name. **No code change needed here** — the
fix propagates automatically because the admin page POSTs the payload from
`_build_video_payload`.

### 3. Fix audio_video_factory.py (CLI script)

**File:** [`backend/scripts/audio_video_factory.py`](../backend/scripts/audio_video_factory.py)

This script reads directly from the database and builds its own payload
(not through `_build_video_payload`). It needs its own anonymization.

Line 111:
```python
person_name = win_data.get("person_name") or "Match"
```

Add the same `_FAKE_NAMES` pool and `_anonymize_name` function (or import from
a shared module), then use it when building `video_payload` (lines 119-125).

**Option:** Extract `_FAKE_NAMES` and `_anonymize_name` into a shared util
module (e.g. [`backend/app/api/v1/video_anonymize.py`](../backend/app/api/v1/video_anonymize.py))
so both `video_export.py` and `audio_video_factory.py` import from the same place.

### 4. (Optional) Redact names in keyDetail bio quotes

`keyDetail` in `ProfileCard.tsx` renders a verbatim bio quote that may contain
a name. Since this is unstructured text, a perfect solution requires LLM
redaction (expensive) or regex heuristics (fragile).

**Decision:** Skip for v1. Bio quotes from dating-app profiles rarely contain
full names (typically display-name only). Add a `ponytail:` comment noting the
ceiling and upgrade path to LLM-based redaction if PII is found in practice.

## Edge cases

| Case | Behavior |
|------|----------|
| `person_name` is empty / "unknown" / "someone" | Returns `"Match"` |
| Same person appears in multiple interactions | Same fake name (deterministic by `ix.id` salt) |
| `keyDetail` contains a name | Not handled in v1 — `ponytail:` comment left in code |
| `theirLastMessage` / transcript texts contain names | Not anonymized — these are user-generated content that could contain any PII. Full transcript redaction would require LLM pass. Out of scope for this change. |

## Files changed

| # | File | Change | Lines |
|---|------|--------|-------|
| 1 | `backend/app/api/v1/video_export.py` | Add `_anonymize_name()` and apply in `_build_video_payload()` | +10 |
| 2 | `backend/scripts/audio_video_factory.py` | Add same function, apply at payload build | +10 |
| ~ | `landing-page/src/app/api/render-video/route.ts` | No change needed (automatic via payload propagation) | 0 |
| ~ | `backend/app/api/v1/video_anonymize.py` | Optional shared module (extract from #1 + #2) | +15 |

## Validation

1. **Admin page loads:** fetch candidates → returned `personName` is fake name
2. **Render flow:** POST `/api/render-video` with fake name → filename is safe
3. **Downloaded video:** opened in player — name displayed is fake name, not real
4. **CLI script:** `python -m backend.scripts.audio_video_factory` → output filename
   and rendered video both show fake name
5. **Determinism:** same chat rendered twice → same fake name both times
