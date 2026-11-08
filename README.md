# WIN365 Telegram Bot

**WIN365 — Football Never Stops!** A football entertainment bot for quizzes, club-guessing challenges, profiles and leaderboards.

## Features
- Daily-style football quiz rounds (5 questions per round)
- Guess-the-club challenge
- Player profiles and non-monetary points
- Global points leaderboard
- Football facts
- SQLite persistence

This project is entertainment only. Points have no cash value and cannot be exchanged or wagered.

## Requirements
- Node.js 20+
- A Telegram bot token from [@BotFather](https://t.me/BotFather)

## Run locally
1. Clone this repository.
2. Install dependencies: `npm install`
3. Copy `.env.example` to `.env`.
4. Add your Telegram token to `BOT_TOKEN` in `.env`.
5. Start the bot: `npm start`

Never commit your `.env` file or share your bot token publicly.

## Deploy
Use a Node.js hosting service. Set `BOT_TOKEN` as a secret environment variable. Set `DATABASE_PATH` to a file on a persistent disk if your host supports persistent storage. Run `npm install` as the build command and `npm start` as the start command.

## Commands
- `/start` — open the main menu
- `/help` — show help
- `/quiz` — start a quiz
- `/profile` — view your profile
- `/leaderboard` — view top players

Live scores, fixtures and football news are not included yet; those require a separate football data provider.
