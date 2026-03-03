#!/usr/bin/env bash
# Render build script — builds the React frontend only
set -o errexit

echo "=== Building frontend ==="
cd website
npm ci
npm run build
cd ..

echo "=== Build complete ==="
