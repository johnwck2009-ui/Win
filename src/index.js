require("dotenv").config();
const fs = require("node:fs");
const path = require("node:path");
const Database = require("better-sqlite3");
const { Telegraf, Markup } = require("telegraf");

const token = process.env.BOT_TOKEN;
if (!token) {
  console.error("BOT_TOKEN is missing. Copy .env.example to .env and add your token.");
  process.exit(1);
}

const bot = new Telegraf(token);
const db = new Database(process.env.DATABASE_PATH || path.join(__dirname, "..", "win365.db"));
db.pragma("journal_mode = WAL");
db.exec(`
  CREATE TABLE IF NOT EXISTS users (
    telegram_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    points INTEGER NOT NULL DEFAULT 0,
    quizzes_played INTEGER NOT NULL DEFAULT 0,
    correct_answers INTEGER NOT NULL DEFAULT 0,
    joined_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
  );
`);

const questions = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "content", "questions.json"), "utf8"));
const sessions = new Map();
const upsertUser = db.prepare(`
  INSERT INTO users (telegram_id, username, first_name) VALUES (@id, @username, @first_name)
  ON CONFLICT(telegram_id) DO UPDATE SET username=excluded.username, first_name=excluded.first_name
`);
const getUser = db.prepare("SELECT * FROM users WHERE telegram_id = ?");
const addScore = db.prepare("UPDATE users SET points = points + ?, correct_answers = correct_answers + ? WHERE telegram_id = ?");
const finishQuiz = db.prepare("UPDATE users SET quizzes_played = quizzes_played + 1 WHERE telegram_id = ?");
const topUsers = db.prepare("SELECT first_name, username, points FROM users ORDER BY points DESC, correct_answers DESC LIMIT 10");

function register(ctx) {
  const u = ctx.from;
  upsertUser.run({ id: u.id, username: u.username || null, first_name: u.first_name || "Football fan" });
}
function mainMenu() {
  return Markup.inlineKeyboard([
    [Markup.button.callback("🧠 Play Daily Quiz", "quiz")],
    [Markup.button.callback("⚽ Guess the Club", "guess_club"), Markup.button.callback("👤 My Profile", "profile")],
    [Markup.button.callback("🏆 Leaderboard", "leaderboard"), Markup.button.callback("📚 Football Facts", "facts")],
    [Markup.button.callback("ℹ️ Help", "help")]
  ]);
}
async function showMenu(ctx, edit = false) {
  const message = `⚽ *WIN365 — Football Never Stops!*

Test your football knowledge, play quick challenges and climb the leaderboard. Ready to play?`;
  if (edit && ctx.callbackQuery) return ctx.editMessageText(message, { parse_mode: "Markdown", ...mainMenu() });
  return ctx.reply(message, { parse_mode: "Markdown", ...mainMenu() });
}
bot.start((ctx) => { register(ctx); return showMenu(ctx); });
bot.command("help", (ctx) => ctx.reply("Use the buttons to play quizzes, guess clubs, view your profile and check the leaderboard. Points are for entertainment only and have no cash value."));
bot.command("quiz", (ctx) => startQuiz(ctx));
bot.command("profile", (ctx) => showProfile(ctx));
bot.command("leaderboard", (ctx) => showLeaderboard(ctx));

async function startQuiz(ctx) {
  register(ctx);
  const pool = [...questions].sort(() => Math.random() - 0.5).slice(0, 5);
  sessions.set(ctx.from.id, { type: "quiz", pool, index: 0, score: 0, answered: false });
  await sendQuestion(ctx);
}
async function sendQuestion(ctx) {
  const s = sessions.get(ctx.from.id);
  if (!s || s.index >= s.pool.length) {
    if (s) {
      finishQuiz.run(ctx.from.id);
      await ctx.reply(`🏁 Quiz complete! You scored ${s.score}/${s.pool.length} and earned ${s.score * 10} points.`, mainMenu());
      sessions.delete(ctx.from.id);
    }
    return;
  }
  const q = s.pool[s.index];
  s.answered = false;
  const keyboard = Markup.inlineKeyboard(q.options.map((option, i) => [Markup.button.callback(option, `answer:${i}`)]));
  await ctx.reply(`🧠 *Question ${s.index + 1}/${s.pool.length}*

${q.question}`, { parse_mode: "Markdown", ...keyboard });
}
bot.action("quiz", async (ctx) => { await ctx.answerCbQuery(); await startQuiz(ctx); });
bot.action(/^answer:(\d+)$/, async (ctx) => {
  const s = sessions.get(ctx.from.id);
  if (!s || s.type !== "quiz" || s.answered) return ctx.answerCbQuery("This question is no longer active.");
  s.answered = true;
  const q = s.pool[s.index];
  const choice = Number(ctx.match[1]);
  const correct = choice === q.answer;
  if (correct) { s.score++; addScore.run(10, 1, ctx.from.id); }
  await ctx.answerCbQuery(correct ? "Correct! +10 points" : "Not quite!");
  await ctx.editMessageReplyMarkup({ inline_keyboard: [] }).catch(() => {});
  await ctx.reply(`${correct ? "✅ Correct!" : `❌ The answer is ${q.options[q.answer]}.`}

💡 ${q.explanation}`, Markup.inlineKeyboard([[Markup.button.callback(s.index === s.pool.length - 1 ? "See results" : "Next question ➡️", "next_question")]]));
});
bot.action("next_question", async (ctx) => {
  await ctx.answerCbQuery();
  const s = sessions.get(ctx.from.id);
  if (!s) return ctx.reply("Start a new quiz from the menu.", mainMenu());
  s.index++;
  await sendQuestion(ctx);
});
bot.action("guess_club", async (ctx) => {
  await ctx.answerCbQuery();
  const clubs = [
    { hint: "I play at the Santiago Bernabéu and have won the European Cup many times.", answer: "Real Madrid" },
    { hint: "My home ground is Old Trafford. I am known as the Red Devils.", answer: "Manchester United" },
    { hint: "Anfield is my home and You'll Never Walk Alone is my anthem.", answer: "Liverpool" },
    { hint: "I play at the Etihad Stadium in Manchester.", answer: "Manchester City" }
  ];
  const item = clubs[Math.floor(Math.random() * clubs.length)];
  sessions.set(ctx.from.id, { type: "club", answer: item.answer });
  await ctx.reply(`⚽ *Guess the club!*

${item.hint}`, { parse_mode: "Markdown", ...Markup.inlineKeyboard([
    ["Real Madrid", "Manchester United"].map(x => Markup.button.callback(x, `club:${x}`)),
    ["Liverpool", "Manchester City"].map(x => Markup.button.callback(x, `club:${x}`))
  ]) });
});
bot.action(/^club:(.+)$/, async (ctx) => {
  const s = sessions.get(ctx.from.id);
  if (!s || s.type !== "club") return ctx.answerCbQuery("Start a new round from the menu.");
  const answer = ctx.match[1];
  sessions.delete(ctx.from.id);
  if (answer === s.answer) { addScore.run(10, 1, ctx.from.id); await ctx.answerCbQuery("Correct! +10 points"); return ctx.reply("🏆 Correct! You earned 10 points.", mainMenu()); }
  await ctx.answerCbQuery("Good try!");
  return ctx.reply(`The correct answer was ${s.answer}. Try another round!`, mainMenu());
});
bot.action("profile", async (ctx) => { await ctx.answerCbQuery(); await showProfile(ctx); });
async function showProfile(ctx) {
  register(ctx);
  const u = getUser.get(ctx.from.id);
  await ctx.reply(`👤 *Your WIN365 Profile*

Name: ${u.first_name}
Points: ${u.points}
Quizzes completed: ${u.quizzes_played}
Correct answers: ${u.correct_answers}

Keep playing to climb the leaderboard!`, { parse_mode: "Markdown", ...mainMenu() });
}
bot.action("leaderboard", async (ctx) => { await ctx.answerCbQuery(); await showLeaderboard(ctx); });
async function showLeaderboard(ctx) {
  const rows = topUsers.all();
  const text = rows.length ? rows.map((u, i) => `${i + 1}. ${u.first_name || u.username || "Player"} — ${u.points} pts`).join("\n") : "No scores yet. Be the first to play!";
  await ctx.reply(`🏆 *WIN365 Leaderboard*

${text}`, { parse_mode: "Markdown", ...mainMenu() });
}
bot.action("facts", async (ctx) => {
  await ctx.answerCbQuery();
  const facts = [
    "The first FIFA World Cup was held in Uruguay in 1930.",
    "A standard football pitch is rectangular, but its exact dimensions can vary within the Laws of the Game.",
    "A hat-trick means a player scores three goals in one match.",
    "The penalty spot is 11 metres from the midpoint of the goal line."
  ];
  await ctx.reply(`📚 *Football Fact*

${facts[Math.floor(Math.random() * facts.length)]}`, { parse_mode: "Markdown", ...mainMenu() });
});
bot.action("help", async (ctx) => { await ctx.answerCbQuery(); await ctx.reply("Choose a game from the menu. Correct quiz and club answers earn non-monetary points. No betting, wagering or cash prizes are part of WIN365.", mainMenu()); });
bot.catch((err) => console.error("Telegram bot error:", err));
bot.launch().then(() => console.log("WIN365 bot is running."));
process.once("SIGINT", () => bot.stop("SIGINT"));
process.once("SIGTERM", () => bot.stop("SIGTERM"));
