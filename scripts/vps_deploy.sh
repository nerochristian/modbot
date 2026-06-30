#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${MODBOT_APP_DIR:-/opt/modbot}"
REPO_URL="${MODBOT_REPO_URL:-https://github.com/nerochristian/modbot.git}"
REMOTE="${MODBOT_REMOTE:-origin}"
BRANCH="${MODBOT_BRANCH:-main}"
SERVICE="${MODBOT_SERVICE:-modbot}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
LOCK_FILE="${MODBOT_DEPLOY_LOCK:-/tmp/modbot-deploy.lock}"
RESET_DIRTY="${MODBOT_DEPLOY_RESET_DIRTY:-0}"

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
  run_as_root_or_user systemctl restart "${SERVICE}"
  run_as_root_or_user systemctl is-active --quiet "${SERVICE}"
}

install_dependencies() {
  if [[ ! -x ".venv/bin/python" ]]; then
    "${PYTHON_BIN}" -m venv .venv
  fi
  .venv/bin/python -m pip install --upgrade pip
  .venv/bin/python -m pip install -r requirements.txt

  if [[ -f "website/package.json" ]] && command -v npm >/dev/null 2>&1; then
    (
      cd website
      if [[ -f package-lock.json ]]; then
        npm ci
      else
        npm install
      fi
      npm run build
    )
  fi
}

compile_check() {
  .venv/bin/python -m compileall -q bot.py cogs utils database.py config.py
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
    git clean -fd -e .env -e .env_remote -e .venv/ -e venv/ -e data/ -e backups/ -e website/dist/
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

  if ! install_dependencies || ! compile_check || ! restart_service; then
    log "Deploy failed; rolling back to ${current_commit}."
    git reset --hard "${current_commit}"
    install_dependencies || true
    compile_check || true
    restart_service || true
    exit 1
  fi

  log "Deploy complete at $(git rev-parse HEAD)."
) 9>"${LOCK_FILE}"
