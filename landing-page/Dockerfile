# ── Cookd Next.js + Remotion Renderer ──
# Self-hosted on Oracle VM. Handles web UI + video rendering.

FROM node:20-slim AS base

# Install Chrome for Remotion (Required for @remotion/renderer)
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-sandbox \
    fonts-ipafont-gothic \
    fonts-wqy-zenhei \
    fonts-thai-tlwg \
    fonts-kacst \
    fonts-freefont-ttf \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true \
    PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium

# ── Dependencies ──
FROM base AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install

# ── Builder ──
FROM deps AS builder
WORKDIR /app
ARG NEXT_PUBLIC_API_BASE_URL
ENV NEXT_PUBLIC_API_BASE_URL=${NEXT_PUBLIC_API_BASE_URL}
ARG NEXT_PUBLIC_POSTHOG_PROJECT_TOKEN
ENV NEXT_PUBLIC_POSTHOG_PROJECT_TOKEN=${NEXT_PUBLIC_POSTHOG_PROJECT_TOKEN}
ARG NEXT_PUBLIC_POSTHOG_HOST
ENV NEXT_PUBLIC_POSTHOG_HOST=${NEXT_PUBLIC_POSTHOG_HOST}
COPY . .
RUN npm run build

# ── Dev (hot reload via bind mount, see docker-compose.yml) ──
FROM deps AS dev
WORKDIR /app
ENV NODE_ENV=development
EXPOSE 3000
CMD ["npm", "run", "dev"]

# ── Production runner ──
FROM base AS runner
WORKDIR /app

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1

RUN addgroup --system --gid 1001 nodejs \
    && adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
# serverExternalPackages (@remotion/renderer, @remotion/bundler, remotion, esbuild)
# contain native binaries that standalone tracing cannot bundle. Copy the full
# node_modules from the deps stage as a fallback — Docker layer caching ensures
# zero deduplication cost, and prevents errors from missing transitive native
# deps (e.g. @rspack/binding pulled by @remotion/bundler).
COPY --from=deps /app/node_modules ./node_modules
# Remotion composition files
COPY --from=builder /app/src/app/admin/remotion ./src/app/admin/remotion

# deps stage runs as root; nextjs user needs write access to node_modules
# for Remotion/rspack cache directories.
RUN chown -R nextjs:nodejs ./node_modules

USER nextjs

EXPOSE 3000
ENV PORT=3000

CMD ["node", "server.js"]
