# bot.py
import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

from agent import get_agent_response
from memory import init_db, save_message, load_history, clear_history
from voice import transcribe_voice  # NEW

load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hey! 👋 I'm your personal AI friend.\nSend me a message to get started."
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name
    user_message = update.message.text
    user_id = str(update.effective_user.id)

    tone = context.user_data.get("tone")

    if not tone:
        keyboard = [
            [InlineKeyboardButton("🤗 Consoling", callback_data="tone_consoling")],
            [InlineKeyboardButton("💪 Firm", callback_data="tone_firm")],
            [InlineKeyboardButton("😄 As a Friend", callback_data="tone_friend")],
            [InlineKeyboardButton("🧠 Objectively", callback_data="tone_objective")],
            [InlineKeyboardButton("🛋️ Therapist", callback_data="tone_therapist")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"Hey {user_name}! 👋\n\nHow would you like me to talk to you today?",
            reply_markup=reply_markup
        )
    else:
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action="typing"
        )
        history = load_history(user_id)
        reply = get_agent_response(user_message, tone, history)
        save_message(user_id, "human", user_message)
        save_message(user_id, "ai", reply)
        await update.message.reply_text(reply)


# ── NEW: VOICE MESSAGE HANDLER ─────────────────────────────────────────
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Runs when user sends a voice message.
    Downloads it, transcribes it, then processes it like a normal text message.
    """
    user_name = update.effective_user.first_name
    user_id = str(update.effective_user.id)
    tone = context.user_data.get("tone")

    # If they haven't picked a tone yet, ask them to first
    if not tone:
        keyboard = [
            [InlineKeyboardButton("🤗 Consoling", callback_data="tone_consoling")],
            [InlineKeyboardButton("💪 Firm", callback_data="tone_firm")],
            [InlineKeyboardButton("😄 As a Friend", callback_data="tone_friend")],
            [InlineKeyboardButton("🧠 Objectively", callback_data="tone_objective")],
            [InlineKeyboardButton("🛋️ Therapist", callback_data="tone_therapist")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"Hey {user_name}! 👋 Pick a tone first, then send your voice message.",
            reply_markup=reply_markup
        )
        return  # stop here — don't process the voice yet

    # Show typing indicator while we download + transcribe
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing"
    )

    # update.message.voice is the Telegram Voice object
    # .get_file() downloads the metadata (not the audio yet)
    # then transcribe_voice() handles the actual download + transcription
    voice = update.message.voice
    file = await context.bot.get_file(voice.file_id)

    # Transcribe — this calls Whisper and returns the text
    transcribed_text = await transcribe_voice(file)

    # Show the user what we heard — good for trust and debugging
    await update.message.reply_text(f"🎤 I heard: _{transcribed_text}_", parse_mode="Markdown")

    # Now treat the transcribed text exactly like a typed message
    history = load_history(user_id)
    reply = get_agent_response(transcribed_text, tone, history)

    # Save with a label so you know it came from voice
    save_message(user_id, "human", f"[voice] {transcribed_text}")
    save_message(user_id, "ai", reply)

    await update.message.reply_text(reply)


async def handle_tone_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    tone = query.data
    context.user_data["tone"] = tone

    tone_messages = {
        "tone_consoling": "I'm here for you 💙 Talk to me, I'm listening.",
        "tone_firm": "Alright. Let's get to it. What's on your mind?",
        "tone_friend": "Yooo what's up!! 😄 Tell me everything.",
        "tone_objective": "Understood. What would you like to discuss?",
        "tone_therapist": "I'm glad you reached out. How are you feeling right now?",
    }

    await query.edit_message_text(tone_messages[tone])


async def change_tone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    context.user_data.pop("tone", None)
    clear_history(user_id)
    await update.message.reply_text("Sure! Send me any message and pick a new tone 👇")


def main():
    init_db()
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("tone", change_tone))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))  # NEW
    app.add_handler(CallbackQueryHandler(handle_tone_selection))

    print("Bot is running... Press Ctrl+C to stop.")
    app.run_polling()


if __name__ == "__main__":
    main()
