# Fix Landing Page Build Error

## Problem

Running `npm run build` in `landing-page/` fails with:

```
Turbopack build failed with 1 errors:
./instrumentation-client.ts:6:5
Return statement is not allowed here
```

Plus a deprecation warning:
```
The "middleware" file convention is deprecated. Please use "proxy" instead.
```

## Root Cause Analysis

### Issue 1: Top-level `return` in [`landing-page/instrumentation-client.ts`](../landing-page/instrumentation-client.ts:6)

The file uses a top-level `return;` statement inside a plain `if` block:

```typescript
if (process.env.NODE_ENV === "production") {
  if (typeof window !== "undefined" && window.location.pathname.startsWith("/admin")) {
    return;  // ❌ SyntaxError: Return statement is not allowed here
  }
  // ...
}
```

Turbopack (Next.js 16's default bundler) strictly enforces module-scope semantics. Top-level `return` is only valid in CommonJS modules, not ESM. The instrumentation hook file is treated as ESM by Turbopack, causing a parse error.

### Issue 2: Middleware deprecation warning

Next.js 16+ deprecates `middleware.ts` (Edge Runtime) in favor of `proxy.ts` (Node.js Runtime). There's currently no middleware/proxy file in the project. The warning appears because Next.js checks for these files at build time.

## Fix Plan

### Fix 1: Refactor `instrumentation-client.ts`

**Approach**: Wrap the top-level logic in an **IIFE (Immediately Invoked Function Expression)** or use a simple **guard clause pattern** that avoids `return`.

The cleanest solution: wrap the entire production block in a self-contained function that can `return` early, or restructure using early-exit with `if/else` without `return`.

**Option A (Recommended)**: Wrap in an IIFE:
```typescript
import posthog from "posthog-js";

(function initPostHog() {
  if (process.env.NODE_ENV !== "production") return;

  // Skip PostHog on admin pages
  if (typeof window !== "undefined" && window.location.pathname.startsWith("/admin")) return;

  const token = process.env.NEXT_PUBLIC_POSTHOG_PROJECT_TOKEN;
  if (!token) {
    console.warn("[PostHog] Skipping init: NEXT_PUBLIC_POSTHOG_PROJECT_TOKEN is not set");
    return;
  }

  posthog.init(token, {
    api_host: "/ph",
    ui_host: "https://us.posthog.com",
    defaults: "2026-01-30",
    capture_exceptions: true,
    capture_pageview: false,
    debug: false,
  });
})();
```

**Option B (Simpler)**: Restructure with guard clauses and no return:
```typescript
import posthog from "posthog-js";

const shouldInit =
  process.env.NODE_ENV === "production" &&
  !(typeof window !== "undefined" && window.location.pathname.startsWith("/admin"));

if (shouldInit) {
  const token = process.env.NEXT_PUBLIC_POSTHOG_PROJECT_TOKEN;
  if (token) {
    posthog.init(token, { /* ... */ });
  } else {
    console.warn("[PostHog] Skipping init: NEXT_PUBLIC_POSTHOG_PROJECT_TOKEN is not set");
  }
}
```

### Fix 2: Middleware → Proxy migration (optional)

The deprecation warning is non-blocking. If a middleware is needed in the future, it should use `proxy.ts` convention. No action required now unless the user wants to address it.

## Verification

1. Run `cd landing-page && npm run build`
2. Confirm no more `Return statement is not allowed here` error
3. Confirm deprecation warning is either gone or acceptable

## Files Changed

| File | Change |
|------|--------|
| [`landing-page/instrumentation-client.ts`](../landing-page/instrumentation-client.ts) | Remove top-level `return` by wrapping in IIFE or guard clause |
