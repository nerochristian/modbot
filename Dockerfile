FROM node:20-bookworm-slim AS dashboard-builder
WORKDIR /build/dashboard
COPY dashboard/package*.json ./
COPY dashboard/prisma ./prisma
RUN npm ci
COPY dashboard/ ./
RUN npm run build

FROM node:20-bookworm-slim AS runtime
WORKDIR /app
ENV NODE_ENV=production \
    PORT=10547 \
    HOSTNAME=0.0.0.0 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/* \
    && npm install --global pm2

COPY requirements.txt ./
RUN pip3 install --break-system-packages --no-cache-dir -r requirements.txt

COPY . ./
RUN rm -rf dashboard/.next dashboard/node_modules
COPY --from=dashboard-builder /build/dashboard/.next/standalone ./dashboard/
COPY --from=dashboard-builder /build/dashboard/.next/static ./dashboard/.next/static
COPY --from=dashboard-builder /build/dashboard/public ./dashboard/public

EXPOSE 10547
CMD ["pm2-runtime", "ecosystem.config.cjs"]
