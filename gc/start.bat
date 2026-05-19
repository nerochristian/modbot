@echo off
setlocal

cd /d "%~dp0"

if not exist ".env" (
    echo Missing .env file. Add your DISCORD_TOKEN before starting the bot.
    pause
    exit /b 1
)

python -m pip install -r requirements.txt
if errorlevel 1 (
    echo Failed to install requirements.
    pause
    exit /b 1
)

python bot.py
if errorlevel 1 (
    echo Bot stopped with an error.
    pause
    exit /b 1
)

endlocal
