#!/usr/bin/env bash
# Render build script — installs Python deps and builds the React frontend
set -o errexit

echo "=== Installing Python dependencies ==="
pip install -r requirements.txt

echo "=== Building frontend ==="
cd website
npm ci
npm run build
cd ..

echo "=== Build complete ==="
