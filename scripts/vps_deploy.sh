#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${MODBOT_APP_DIR:-/opt/modbot}"
REPO_URL="${MODBOT_REPO_URL:-https://github.com/nerochristian/modbot.git}"
REMOTE="${MODBOT_REMOTE:-origin}"
BRANCH="${MODBOT_BRANCH:-main}"
SERVICE="${MODBOT_SERVICE:-modbot}"
BOT_ENTRYPOINT="${MODBOT_ENTRYPOINT:-bot.py}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
LOCK_FILE="${MODBOT_DEPLOY_LOCK:-/tmp/${SERVICE}-deploy.lock}"
RESET_DIRTY="${MODBOT_DEPLOY_RESET_DIRTY:-0}"

SERVICE="${SERVICE%.service}"

case "${SERVICE}" in
  ""|modbot-autoupdate|*-autoupdate)
    echo "Invalid MODBOT_SERVICE='${SERVICE}'. Use the actual bot systemd service name." >&2
    exit 1
    ;;
esac

log() {
  printf '[%s] %s\n' "$(date -Is)" "$*"
}

run_as_root_or_user() {
  if [[ "${EUID}" -eq 0 ]]; then
    "$@"
  elif command -v sudo >/dev/null 2>&1; then
    sudo "$@"
  else
    "$@"
  fi
}

restart_service() {
  run_as_root_or_user systemctl daemon-reload
  if ! run_as_root_or_user systemctl cat "${SERVICE}" >/dev/null 2>&1; then
    log "Service ${SERVICE} does not exist. Refusing to restart a wrong bot."
    exit 1
  fi
  run_as_root_or_user systemctl restart "${SERVICE}"
  run_as_root_or_user systemctl is-active --quiet "${SERVICE}"
}

install_bot_dependencies() {
  if [[ ! -x ".venv/bin/python" ]]; then
    "${PYTHON_BIN}" -m venv .venv
  fi
  .venv/bin/python -m pip install --upgrade pip
  .venv/bin/python -m pip install -r requirements.txt

  if grep -q "playwright" requirements.txt; then
    .venv/bin/python -m playwright install chromium
  fi
}

build_dashboard() {
  if [[ -f "dashboard/package.json" ]] && command -v npm >/dev/null 2>&1; then
    (
      cd dashboard
      mkdir -p data
      # The dashboard connects through the libSQL adapter, so its Prisma URL must
      # be a file:/libsql: URL — distinct from the bot's postgres DATABASE_URL.
      # Export both before npm ci so Prisma's postinstall generate can resolve it
      # (there is no dashboard/.env to fall back on).
      export DASHBOARD_DATABASE_URL="${DASHBOARD_DATABASE_URL:-file:${APP_DIR}/dashboard/data/dashboard.db}"
      export DATABASE_URL="${DASHBOARD_DATABASE_URL}"
      npm ci
      if [[ "${DATABASE_URL}" == file:* ]]; then
        dashboard_db_path="${DATABASE_URL#file:}"
        legacy_db="${APP_DIR}/dashboard/.next/standalone/dev.db"
        if [[ ! -f "${dashboard_db_path}" && -f "${legacy_db}" ]]; then
          mkdir -p "$(dirname "${dashboard_db_path}")"
          cp -p "${legacy_db}" "${dashboard_db_path}"
        fi
      fi
      # Existing dashboard databases predate Prisma Migrate. Baseline them once,
      # then apply only tracked forward migrations. Fresh databases apply the
      # baseline normally.
      if node -e '
        const { createClient } = require("@libsql/client");
        const db = createClient({ url: process.env.DATABASE_URL });
        Promise.all([
          db.execute({
            sql: "SELECT COUNT(*) AS count FROM sqlite_master WHERE type = ? AND name NOT LIKE ?",
            args: ["table", "sqlite_%"],
          }),
          db.execute({
            sql: "SELECT COUNT(*) AS count FROM sqlite_master WHERE type = ? AND name = ?",
            args: ["table", "_prisma_migrations"],
          }),
        ]).then(([tables, migrations]) => {
          const hasTables = Number(tables.rows[0].count) > 0;
          const hasMigrations = Number(migrations.rows[0].count) > 0;
          process.exit(hasTables && !hasMigrations ? 0 : 1);
        }).catch(() => process.exit(1));
      '; then
        npx prisma migrate resolve --applied 20260712160000_baseline
      fi
      npx prisma migrate deploy
      # Explicit generate guards against a skipped/failed postinstall — without a
      # client the TypeScript build fails and the dashboard 502s.
      npx prisma generate
      npm run build
      rm -f .next/standalone/.env .next/standalone/.env.local \
        .next/standalone/.env.production .next/standalone/.env.production.local
      mkdir -p .next/standalone/.next
      cp -a .next/static .next/standalone/.next/
      cp -a public .next/standalone/
    )
  fi
}

restart_dashboard() {
  if command -v pm2 >/dev/null 2>&1; then
    mkdir -p "${APP_DIR}/dashboard/data"
    pm2 startOrReload ecosystem.config.cjs --only modbot-dashboard --update-env
    pm2 save
    pm2 describe modbot-dashboard >/dev/null
  fi
}

compile_check() {
  if [[ ! -f "${BOT_ENTRYPOINT}" ]]; then
    log "Configured entrypoint ${BOT_ENTRYPOINT} does not exist in ${APP_DIR}."
    exit 1
  fi
  .venv/bin/python -m compileall -q "${BOT_ENTRYPOINT}" cogs utils database.py config.py
}

(
  flock -n 9 || {
    log "Another deploy is already running."
    exit 0
  }

  if [[ ! -d "${APP_DIR}/.git" ]]; then
    log "Cloning ${REPO_URL} into ${APP_DIR}."
    mkdir -p "$(dirname "${APP_DIR}")"
    git clone --branch "${BRANCH}" "${REPO_URL}" "${APP_DIR}"
  fi

  cd "${APP_DIR}"

  if [[ "${RESET_DIRTY}" == "1" ]]; then
    git reset --hard
    git clean -fd -e .env -e .env_remote -e .venv/ -e venv/ -e data/ -e backups/ -e dashboard/dev.db
  elif [[ -n "$(git status --porcelain --untracked-files=no)" ]]; then
    log "Refusing to deploy because tracked files are dirty. Set MODBOT_DEPLOY_RESET_DIRTY=1 to discard tracked VPS edits."
    git status --short
    exit 1
  fi

  current_commit="$(git rev-parse HEAD)"
  log "Fetching ${REMOTE}/${BRANCH}."
  git fetch --prune "${REMOTE}" "${BRANCH}"
  target_commit="$(git rev-parse "${REMOTE}/${BRANCH}")"

  if [[ "${current_commit}" == "${target_commit}" ]]; then
    log "Already up to date at ${current_commit}."
    exit 0
  fi

  log "Deploying ${current_commit} -> ${target_commit}."
  git merge --ff-only "${REMOTE}/${BRANCH}"

  # Only rebuild/restart the components whose files actually changed. The
  # auto-update timer fires every 60s and most commits touch scratch/, tests/,
  # or docs — none of which affect the running services. Rebuilding the
  # dashboard unconditionally cost a ~2-minute `npm ci`/build every couple of
  # minutes, rotated Next.js Server Action IDs (breaking open browser sessions
  # with "Failed to find Server Action"), and bounced the bot's gateway link.
  changed_files="$(git diff --name-only "${current_commit}" "${target_commit}" || true)"
  bot_changed=0
  dashboard_changed=0
  if grep -qE '^(bot\.py|database\.py|config\.py|requirements\.txt|cogs/|utils/)' <<<"${changed_files}"; then
    bot_changed=1
  fi
  if grep -qE '^(dashboard/|ecosystem\.config\.cjs)' <<<"${changed_files}"; then
    dashboard_changed=1
  fi

  if [[ "${bot_changed}" -eq 0 && "${dashboard_changed}" -eq 0 ]]; then
    log "No runtime-relevant changes (updated tree only); skipping rebuild/restart."
    log "Deploy complete at $(git rev-parse HEAD)."
    exit 0
  fi

  deploy_ok=1
  if [[ "${bot_changed}" -eq 1 ]]; then
    log "Bot sources changed; installing deps, compiling, restarting ${SERVICE}."
    { install_bot_dependencies && compile_check && restart_service; } || deploy_ok=0
  fi
  if [[ "${deploy_ok}" -eq 1 && "${dashboard_changed}" -eq 1 ]]; then
    log "Dashboard sources changed; rebuilding and reloading dashboard."
    { build_dashboard && restart_dashboard; } || deploy_ok=0
  fi

  if [[ "${deploy_ok}" -ne 1 ]]; then
    log "Deploy failed; rolling back to ${current_commit}."
    git reset --hard "${current_commit}"
    if [[ "${bot_changed}" -eq 1 ]]; then
      install_bot_dependencies || true
      compile_check || true
      restart_service || true
    fi
    if [[ "${dashboard_changed}" -eq 1 ]]; then
      build_dashboard || true
      restart_dashboard || true
    fi
    exit 1
  fi

  log "Deploy complete at $(git rev-parse HEAD)."
) 9>"${LOCK_FILE}"
