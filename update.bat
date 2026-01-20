@echo off
:: Navigate to the script's directory
cd /d "%~dp0"

echo ==========================================
echo  Git Auto-Sync Script
echo ==========================================

:: 1. Pull latest changes from GitHub (The Fix)
echo Pulling latest changes from GitHub...
git pull origin main

:: 2. Add all local changes
echo Adding changes...
git add .

:: 3. Commit (only if there are changes)
set datetime=%date% %time%
echo Committing changes at %datetime%...
git commit -m "Auto update: %datetime%"

:: 4. Push to GitHub
echo Pushing to remote...
git push origin main

echo ==========================================
echo  Done!
pause