# WIN365 Telegram Bot

**WIN365 — Football Never Stops!** A football entertainment bot for quizzes, club-guessing challenges, profiles and leaderboards.

## Features
- Football quiz rounds (5 questions per round)
- Guess-the-club challenge
- Player profiles and non-monetary points
- Global points leaderboard
- Football facts
- SQLite database for player scores and profiles

This project is for entertainment only. Points have no cash value and cannot be exchanged or wagered.

## Requirements
- Python 3.10+
- A Telegram bot token from [@BotFather](https://t.me/BotFather)

## Run locally
1. Clone this repository.
2. Install dependencies: `pip install -r requirements.txt`
3. Copy `.env.example` to `.env`.
4. Add your Telegram token to `BOT_TOKEN` in `.env`.
5. Start the bot: `python bot.py`

Never commit your `.env` file or share your bot token publicly.

## Deploy on Render
Create a **Background Worker** connected to this repository.

- Runtime: Python
- Root Directory: leave blank
- Build Command: `pip install -r requirements.txt`
- Start Command: `python bot.py`

Add `BOT_TOKEN` in the Render Environment Variables section. For persistent SQLite data, attach a persistent disk mounted at `/var/data` and add `DATABASE_PATH=/var/data/win365.db` as an environment variable. Without persistent storage, the database may be lost when the service is replaced.

## Commands
- `/start` — open the main menu
- `/help` — show help
- `/quiz` — start a quiz
- `/profile` — view your profile
- `/leaderboard` — view top players

Live scores, fixtures and football news are not included yet; those require a separate football data provider.
