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
# remotion/@remotion/renderer are serverExternalPackages (native binaries) —
# standalone tracing doesn't bundle them, so pull the real packages in from deps
COPY --from=deps /app/node_modules/remotion ./node_modules/remotion
COPY --from=deps /app/node_modules/@remotion ./node_modules/@remotion
# Remotion composition files
COPY --from=builder /app/src/app/admin/remotion ./src/app/admin/remotion

USER nextjs

EXPOSE 3000
ENV PORT=3000

CMD ["node", "server.js"]
