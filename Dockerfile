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
    DASHBOARD_HOSTNAME=0.0.0.0 \
    DASHBOARD_DATABASE_URL=file:/app/dashboard/data/dashboard.db \
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
COPY --from=dashboard-builder /build/dashboard/node_modules ./dashboard/node_modules
COPY --from=dashboard-builder /build/dashboard/.next/standalone ./dashboard/.next/standalone
COPY --from=dashboard-builder /build/dashboard/.next/static ./dashboard/.next/standalone/.next/static
COPY --from=dashboard-builder /build/dashboard/public ./dashboard/.next/standalone/public
RUN mkdir -p dashboard/data

EXPOSE 10547
CMD ["sh", "-c", "set -e; cd /app/dashboard; if node -e 'const {createClient}=require(\"@libsql/client\"); const db=createClient({url:process.env.DASHBOARD_DATABASE_URL}); Promise.all([db.execute({sql:\"SELECT COUNT(*) AS count FROM sqlite_master WHERE type = ? AND name NOT LIKE ?\",args:[\"table\",\"sqlite_%\"]}),db.execute({sql:\"SELECT COUNT(*) AS count FROM sqlite_master WHERE type = ? AND name = ?\",args:[\"table\",\"_prisma_migrations\"]})]).then(([tables,migrations])=>process.exit(Number(tables.rows[0].count)>0&&Number(migrations.rows[0].count)===0?0:1)).catch(()=>process.exit(1))'; then npx prisma migrate resolve --applied 20260712160000_baseline; fi; npx prisma migrate deploy; cd /app; exec pm2-runtime ecosystem.config.cjs"]
