@echo off
:: Navigate to the script's directory (your repo folder)
cd /d "%~dp0"

echo ==========================================
echo  Git Auto-Sync Script
echo ==========================================

:: 1. Add all changes
echo Adding changes...
git add .

:: 2. Get current date and time for the commit message
set datetime=%date% %time%
echo Committing changes at %datetime%...

:: 3. Commit
git commit -m "Auto update: %datetime%"

:: 4. Push to GitHub (Change 'main' to 'master' if your branch is named master)
echo Pushing to remote...
git push origin main

echo ==========================================
echo  Done!
pause