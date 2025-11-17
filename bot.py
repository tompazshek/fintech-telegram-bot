import json
import random
from datetime import time
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

ABBREVIATIONS = [
    ("FCA", "Financial Conduct Authority"),
    ("PSD2", "Revised Payment Services Directive"),
    ("API", "Application Programming Interface"),
    ("KYC", "Know Your Customer"),
    ("AML", "Anti-Money Laundering"),
    ("CMA", "Competition and Markets Authority"),
    ("BACS", "Bankers’ Automated Clearing Services"),
    ("CHAPS", "Clearing House Automated Payment System"),
    ("FOS", "Financial Ombudsman Service"),
    ("FPC", "Financial Policy Committee"),
]

DB_FILE = "data.json"

def load_db():
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_db(db):
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=2)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    db = load_db()

    if user_id not in db:
        db[user_id] = {
            "day": 0,
        }
        save_db(db)

    await update.message.reply_text(
        "Welcome! I will send 5 new UK fintech abbreviations every day and a weekly quiz!"
    )


async def send_daily(context):
    db = load_db()
    bot = context.bot

    for user_id, data in db.items():
        day = data["day"]
        start_i = day * 5
        end_i = start_i + 5

        if start_i >= len(ABBREVIATIONS):
            continue

        chunk = ABBREVIATIONS[start_i:end_i]
        msg = "📘 *Today's UK Fintech Abbreviations:*\n\n"
        for abbr, desc in chunk:
            msg += f"*{abbr}* — {desc}\n"

        await bot.send_message(chat_id=int(user_id), text=msg, parse_mode="Markdown")

        db[user_id]["day"] += 1

    save_db(db)


async def send_quiz(context):
    bot = context.bot
    db = load_db()

    for user_id in db:
        sample = random.sample(ABBREVIATIONS, 5)
        db[user_id]["quiz"] = sample
        save_db(db)

        text = "📝 *Weekly Quiz!* What do these stand for?\n\n"
        for i, (abbr, _) in enumerate(sample):
            text += f"{i+1}. {abbr}\n"

        text += "\nReply like this:\n1:..., 2:..., 3:..., 4:..., 5:..."

        await bot.send_message(chat_id=int(user_id), text=text, parse_mode="Markdown")


async def quiz_handler(update: Update, context):
    user_id = str(update.effective_user.id)
    db = load_db()

    if "quiz" not in db.get(user_id, {}):
        return

    answers = update.message.text.split(",")
    quiz = db[user_id]["quiz"]
    correct = 0

    for i, part in enumerate(answers):
        if ":" not in part:
            continue
        user_answer = part.split(":")[1].strip().lower()
        real = quiz[i][1].lower()
        if user_answer in real:
            correct += 1

    await update.message.reply_text(f"Your quiz score is: {correct}/5 🎉")

    del db[user_id]["quiz"]
    save_db(db)


def main():
    import os

    TOKEN = os.environ["BOT_TOKEN"]

    app = ApplicationBuilder().token(TOKEN).build()

    scheduler = AsyncIOScheduler()
    scheduler.add_job(send_daily, "cron", hour=9, minute=0, args=[app.bot])
    scheduler.add_job(send_quiz, "cron", day_of_week="sun", hour=10, minute=0, args=[app.bot])
    scheduler.start()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), quiz_handler))

    app.run_polling()


if __name__ == "__main__":
    main()
