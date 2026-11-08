import json
import logging
import os
import random
import sqlite3
from pathlib import Path

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

load_dotenv()
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("BOT_TOKEN is missing. Add it to your Render environment variables.")

BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", str(BASE_DIR / "win365.db")))
DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
QUESTIONS_PATH = BASE_DIR / "content" / "questions.json"

with QUESTIONS_PATH.open("r", encoding="utf-8") as file:
    QUESTIONS = json.load(file)

CLUBS = [
    ("I play at the Santiago Bernabéu and have won the European Cup many times.", "Real Madrid"),
    ("My home ground is Old Trafford. I am known as the Red Devils.", "Manchester United"),
    ("Anfield is my home and You'll Never Walk Alone is my anthem.", "Liverpool"),
    ("I play at the Etihad Stadium in Manchester.", "Manchester City"),
]
FACTS = [
    "The first FIFA World Cup was held in Uruguay in 1930.",
    "A standard football pitch is rectangular, but its exact dimensions can vary within the Laws of the Game.",
    "A hat-trick means a player scores three goals in one match.",
    "The penalty spot is 11 metres from the midpoint of the goal line.",
]


def connect_db():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    with connect_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                points INTEGER NOT NULL DEFAULT 0,
                quizzes_played INTEGER NOT NULL DEFAULT 0,
                correct_answers INTEGER NOT NULL DEFAULT 0,
                joined_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)


def register_user(user):
    with connect_db() as db:
        db.execute("""
            INSERT INTO users (telegram_id, username, first_name)
            VALUES (?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                username=excluded.username,
                first_name=excluded.first_name
        """, (user.id, user.username, user.first_name or "Football fan"))


def add_score(user_id, points, correct=1):
    with connect_db() as db:
        db.execute(
            "UPDATE users SET points = points + ?, correct_answers = correct_answers + ? WHERE telegram_id = ?",
            (points, correct, user_id),
        )


def menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🧠 Play Daily Quiz", callback_data="quiz")],
        [
            InlineKeyboardButton("⚽ Guess the Club", callback_data="guess_club"),
            InlineKeyboardButton("👤 My Profile", callback_data="profile"),
        ],
        [
            InlineKeyboardButton("🏆 Leaderboard", callback_data="leaderboard"),
            InlineKeyboardButton("📚 Football Facts", callback_data="facts"),
        ],
        [InlineKeyboardButton("ℹ️ Help", callback_data="help")],
    ])


async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = (
        "⚽ WIN365 — Football Never Stops!\n\n"
        "Test your football knowledge, play quick challenges and climb the leaderboard. Ready to play?"
    )
    if update.callback_query:
        await update.callback_query.message.reply_text(message, reply_markup=menu_keyboard())
    else:
        await update.effective_message.reply_text(message, reply_markup=menu_keyboard())


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    register_user(update.effective_user)
    await show_menu(update, context)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        "Use the buttons to play quizzes, guess clubs, view your profile and check the leaderboard. "
        "Points are for entertainment only and have no cash value.",
        reply_markup=menu_keyboard(),
    )


async def start_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    register_user(user)
    pool = random.sample(QUESTIONS, min(5, len(QUESTIONS)))
    context.user_data["game"] = {
        "type": "quiz",
        "user_id": user.id,
        "pool": pool,
        "index": 0,
        "score": 0,
        "answered": False,
    }
    await send_question(update.effective_message, context)


async def send_question(message, context: ContextTypes.DEFAULT_TYPE):
    game = context.user_data.get("game")
    if not game or game["index"] >= len(game["pool"]):
        if game:
            with connect_db() as db:
                db.execute(
                    "UPDATE users SET quizzes_played = quizzes_played + 1 WHERE telegram_id = ?",
                    (game["user_id"],),
                )
            await message.reply_text(
                f"🏁 Quiz complete! You scored {game['score']}/{len(game['pool'])} "
                f"and earned {game['score'] * 10} points.",
                reply_markup=menu_keyboard(),
            )
            context.user_data.pop("game", None)
        return

    question = game["pool"][game["index"]]
    game["answered"] = False
    buttons = [
        [InlineKeyboardButton(option, callback_data=f"answer:{i}")]
        for i, option in enumerate(question["options"])
    ]
    await message.reply_text(
        f"🧠 Question {game['index'] + 1}/{len(game['pool'])}\n\n{question['question']}",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def quiz_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start_quiz(update, context)


async def guess_club(update: Update, context: ContextTypes.DEFAULT_TYPE):
    item = random.choice(CLUBS)
    context.user_data["game"] = {"type": "club", "answer": item[1]}
    options = ["Real Madrid", "Manchester United", "Liverpool", "Manchester City"]
    random.shuffle(options)
    keyboard = [
        [InlineKeyboardButton(name, callback_data=f"club:{name}")]
        for name in options
    ]
    await update.effective_message.reply_text(
        f"⚽ Guess the club!\n\n{item[0]}",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    register_user(user)
    with connect_db() as db:
        row = db.execute("SELECT * FROM users WHERE telegram_id = ?", (user.id,)).fetchone()
    await update.effective_message.reply_text(
        f"👤 Your WIN365 Profile\n\nName: {row['first_name']}\n"
        f"Points: {row['points']}\nQuizzes completed: {row['quizzes_played']}\n"
        f"Correct answers: {row['correct_answers']}\n\nKeep playing to climb the leaderboard!",
        reply_markup=menu_keyboard(),
    )


async def show_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with connect_db() as db:
        rows = db.execute(
            "SELECT first_name, username, points FROM users "
            "ORDER BY points DESC, correct_answers DESC LIMIT 10"
        ).fetchall()
    if rows:
        lines = [
            f"{i}. {row['first_name'] or row['username'] or 'Player'} — {row['points']} pts"
            for i, row in enumerate(rows, start=1)
        ]
        result = "\n".join(lines)
    else:
        result = "No scores yet. Be the first to play!"
    await update.effective_message.reply_text(
        f"🏆 WIN365 Leaderboard\n\n{result}",
        reply_markup=menu_keyboard(),
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = update.effective_user.id

    if data == "quiz":
        await start_quiz(update, context)
    elif data == "guess_club":
        await guess_club(update, context)
    elif data == "profile":
        await show_profile(update, context)
    elif data == "leaderboard":
        await show_leaderboard(update, context)
    elif data == "facts":
        await query.message.reply_text(
            f"📚 Football Fact\n\n{random.choice(FACTS)}",
            reply_markup=menu_keyboard(),
        )
    elif data == "help":
        await help_command(update, context)
    elif data.startswith("answer:"):
        game = context.user_data.get("game")
        if not game or game.get("type") != "quiz" or game.get("answered"):
            await query.message.reply_text("This question is no longer active. Start a new quiz from the menu.")
            return
        game["answered"] = True
        question = game["pool"][game["index"]]
        selected = int(data.split(":", 1)[1])
        correct = selected == question["answer"]
        if correct:
            game["score"] += 1
            add_score(user_id, 10, 1)
            feedback = "✅ Correct! +10 points"
        else:
            feedback = f"❌ The answer is {question['options'][question['answer']]}."
        await query.edit_message_reply_markup(reply_markup=None)
        next_label = "See results" if game["index"] == len(game["pool"]) - 1 else "Next question ➡️"
        await query.message.reply_text(
            f"{feedback}\n\n💡 {question['explanation']}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(next_label, callback_data="next_question")
            ]]),
        )
    elif data == "next_question":
        game = context.user_data.get("game")
        if not game or game.get("type") != "quiz":
            await query.message.reply_text("Start a new quiz from the menu.", reply_markup=menu_keyboard())
            return
        game["index"] += 1
        await send_question(query.message, context)
    elif data.startswith("club:"):
        game = context.user_data.get("game")
        if not game or game.get("type") != "club":
            await query.message.reply_text("Start a new round from the menu.")
            return
        answer = data.split(":", 1)[1]
        correct = answer == game["answer"]
        context.user_data.pop("game", None)
        if correct:
            add_score(user_id, 10, 1)
            message = "🏆 Correct! You earned 10 points."
        else:
            message = f"Good try! The correct answer was {game['answer']}."
        await query.message.reply_text(message, reply_markup=menu_keyboard())


def main():
    init_db()
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("quiz", quiz_command))
    application.add_handler(CommandHandler("profile", show_profile))
    application.add_handler(CommandHandler("leaderboard", show_leaderboard))
    application.add_handler(CallbackQueryHandler(button_handler))
    logger.info("Starting WIN365 Telegram bot...")
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
