@echo off
setlocal

cd /d "%~dp0"

echo ==========================================
echo  Banana Server Bot Starter
echo ==========================================
echo.

set "PYTHON_EXE="

if exist ".venv\Scripts\python.exe" (
  set "PYTHON_EXE=.venv\Scripts\python.exe"
) else if exist "venv\Scripts\python.exe" (
  set "PYTHON_EXE=venv\Scripts\python.exe"
)

if defined PYTHON_EXE (
  echo Using virtual environment: %PYTHON_EXE%
  "%PYTHON_EXE%" bot.py
) else (
  where py >nul 2>&1
  if not errorlevel 1 (
    echo Using launcher: py -3
    py -3 bot.py
  ) else (
    where python >nul 2>&1
    if errorlevel 1 (
      echo [ERROR] Python was not found in PATH and no venv was detected.
      echo Install Python or create a venv first.
      pause
      exit /b 1
    )
    echo Using system python
    python bot.py
  )
)

set "EXIT_CODE=%ERRORLEVEL%"
echo.
echo Bot exited with code %EXIT_CODE%.
pause
exit /b %EXIT_CODE%
