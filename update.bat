@echo off
setlocal ENABLEDELAYEDEXPANSION

cd /d "%~dp0"

set "REPO_URL=https://github.com/nerochristian/modbot"
set "DEFAULT_BRANCH=main"

echo ==========================================
echo  Banana Server Updater
echo ==========================================
echo Target repo: %REPO_URL%
echo.

where git >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Git is not installed or not in PATH.
  pause
  exit /b 1
)

if not exist ".git" (
  echo No Git repository found. Initializing...
  git init
  if errorlevel 1 (
    echo [ERROR] Failed to initialize Git repository.
    pause
    exit /b 1
  )
  git checkout -B %DEFAULT_BRANCH% >nul 2>&1
  if errorlevel 1 (
    git branch -M %DEFAULT_BRANCH% >nul 2>&1
  )
)

git remote get-url origin >nul 2>&1
if errorlevel 1 (
  echo Adding origin remote...
  git remote add origin "%REPO_URL%"
) else (
  echo Setting origin remote...
  git remote set-url origin "%REPO_URL%"
)

set "CURRENT_BRANCH=%DEFAULT_BRANCH%"
git checkout -B "%CURRENT_BRANCH%" >nul 2>&1

echo Current branch: %CURRENT_BRANCH%
echo.
echo Staging local changes...
git add -A

git diff --cached --quiet
if errorlevel 1 (
  set "NOW=%date% %time%"
  echo Creating commit...
  git commit -m "Update: %NOW%"
  if errorlevel 1 (
    echo [ERROR] Commit failed.
    echo Make sure git user is configured:
    echo   git config --global user.name "Your Name"
    echo   git config --global user.email "you@example.com"
    pause
    exit /b 1
  )
) else (
  echo No local changes to commit.
)

echo Pushing to origin/%CURRENT_BRANCH%...
git push -u origin "%CURRENT_BRANCH%"
if errorlevel 1 (
  echo [ERROR] Push failed.
  pause
  exit /b 1
)

echo.
echo ==========================================
echo  Push complete.
echo ==========================================
pause
