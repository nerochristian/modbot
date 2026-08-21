# Docket moderation bot

Discord moderation bot and dashboard with AI moderation powered by OpenRouter.
Talking, live search, vision, research, and the protected moderation lane each
run on their own OpenRouter model, so retuning one cannot take over another.

## Run Locally

**Prerequisites:** Python 3.11+ and Node.js


1. Copy `.env.example` to `.env` and configure the Discord and database values.
2. Install the bot dependencies with `python -m pip install -r requirements.txt`.
3. Install the browser runtime with `python -m playwright install chromium`.
4. Install dashboard dependencies with `npm install`.
5. Start the bot with `python bot.py` and the dashboard with `npm run dev`.
