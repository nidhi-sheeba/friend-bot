# bot.py
import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

from agent import get_agent_response
from image_handler import interpret_image
from memory import init_db, save_message, load_history, clear_history
from voice import transcribe_voice

load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")


# ── HELPER: TONE KEYBOARD ──────────────────────────────────────────────
def tone_keyboard():
    """Returns the tone selection keyboard — reused in multiple places"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🤗 Consoling", callback_data="tone_consoling")],
        [InlineKeyboardButton("💪 Firm", callback_data="tone_firm")],
        [InlineKeyboardButton("😄 As a Friend", callback_data="tone_friend")],
        [InlineKeyboardButton("🧠 Objectively", callback_data="tone_objective")],
        [InlineKeyboardButton("🛋️ Therapist", callback_data="tone_therapist")],
    ])


# ── HANDLER 1: /start ──────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    user_name = update.effective_user.first_name

    await update.message.reply_text(
        f"Hey {user_name}! 👋 I'm your personal AI friend.\n\nHow would you like me to talk to you today?",
        reply_markup=tone_keyboard()
    )

async def clear_memory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    user_id = str(update.effective_user.id)
    clear_history(user_id)
    await update.message.reply_text("🗑️ Memory cleared! I've forgotten our conversation history.")

# ── HANDLER 2: Text messages ───────────────────────────────────────────
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    user_name = update.effective_user.first_name
    user_message = update.message.text
    user_id = str(update.effective_user.id)

    tone = context.user_data.get("tone")

    if not tone:
        await update.message.reply_text(
            f"Hey {user_name}! 👋\n\nHow would you like me to talk to you today?",
            reply_markup=tone_keyboard()
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


# ── HANDLER 3: Voice messages ──────────────────────────────────────────
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    user_name = update.effective_user.first_name
    user_id = str(update.effective_user.id)
    tone = context.user_data.get("tone")

    if not tone:
        await update.message.reply_text(
            f"Hey {user_name}! 👋 Pick a tone first, then send your voice message.",
            reply_markup=tone_keyboard()
        )
        return

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing"
    )

    voice = update.message.voice
    file = await context.bot.get_file(voice.file_id)
    transcribed_text = await transcribe_voice(file)

    await update.message.reply_text(f"🎤 I heard: _{transcribed_text}_", parse_mode="Markdown")

    history = load_history(user_id)
    reply = get_agent_response(transcribed_text, tone, history)

    save_message(user_id, "human", f"[voice] {transcribed_text}")
    save_message(user_id, "ai", reply)

    await update.message.reply_text(reply)

# ── HANDLER: Photo messages ────────────────────────────────────────────
async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    user_id = str(update.effective_user.id)
    tone = context.user_data.get("tone")

    if not tone:
        await update.message.reply_text(
            "Pick a tone first, then send your image!",
            reply_markup=tone_keyboard()
        )
        return

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing"
    )

    # Get the highest resolution version of the photo
    # Telegram sends multiple sizes — [-1] is always the largest
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)

    # Caption is optional text the user sends with the image
    caption = update.message.caption or ""

    # Get tone prompt for personality
    from llm import TONE_PROMPTS
    tone_prompt = TONE_PROMPTS.get(tone, TONE_PROMPTS["tone_friend"])

    reply = await interpret_image(file, caption, tone_prompt)

    # Save to memory so the bot remembers the image was discussed
    save_message(user_id, "human", f"[image] {caption}" if caption else "[image sent]")
    save_message(user_id, "ai", reply)

    await update.message.reply_text(reply)
# ── HANDLER 4: Tone button clicks ─────────────────────────────────────
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


# ── HANDLER 5: /tone command ───────────────────────────────────────────
async def change_tone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    user_id = str(update.effective_user.id)
    context.user_data.pop("tone", None)
    clear_history(user_id)

    await update.message.reply_text(
        "Sure! How would you like me to talk to you?",
        reply_markup=tone_keyboard()
    )


# ── MAIN ───────────────────────────────────────────────────────────────
def main():
    init_db()
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("tone", change_tone))
    app.add_handler(MessageHandler(filters.PHOTO, handle_image))
    app.add_handler(CommandHandler("clear", clear_memory))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(CallbackQueryHandler(handle_tone_selection))

    print("Bot is running... Press Ctrl+C to stop.")
    app.run_polling()


if __name__ == "__main__":
    main()
