import os
from telegram import (
    Update, InlineKeyboardMarkup, InlineKeyboardButton,
    InputMediaPhoto, InputMediaVideo, ReplyKeyboardRemove
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters, CallbackQueryHandler
)

# Простая структура хранения поста (в памяти)
user_drafts = {}

CHANNEL_ID = "@adpanx"  # или "-1001234567890"

def get_preview_markup():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📤 Опубликовать", callback_data="publish")],
        [InlineKeyboardButton("✏️ Редактировать текст", callback_data="edit_text")],
        [InlineKeyboardButton("🗑️ Удалить черновик", callback_data="delete_draft")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Отправь мне текст или фото — я подготовлю пост с предпросмотром.")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_drafts:
        user_drafts[user_id] = {}

    user_drafts[user_id]['text'] = update.message.text
    await update.message.reply_text(
    f"📄 Черновик обновлён. Вот как будет выглядеть пост:\n\n{update.message.text}",
    reply_markup=get_preview_markup()
)
    
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    photo_file_id = update.message.photo[-1].file_id  # берём наибольшее качество

    if user_id not in user_drafts:
        user_drafts[user_id] = {}

    user_drafts[user_id]['photo'] = photo_file_id
    user_drafts[user_id]['caption'] = update.message.caption or user_drafts[user_id].get('text', '')

    await update.message.reply_photo(
        photo=photo_file_id,
        caption=f"📸 Предпросмотр поста:\n\n{user_drafts[user_id]['caption']}",
        reply_markup=get_preview_markup()
    )

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    draft = user_drafts.get(user_id)

    if query.data == "publish":
        if not draft:
            await query.edit_message_text("❗ Нет черновика для публикации.")
            return
        try:
            if 'photo' in draft:
                await context.bot.send_photo(
                    chat_id=CHANNEL_ID,
                    photo=draft['photo'],
                    caption=draft.get('caption', '')
                )
            else:
                await context.bot.send_message(
                    chat_id=CHANNEL_ID,
                    text=draft.get('text', '')
                )
            await query.edit_message_text("✅ Пост опубликован.")
            user_drafts.pop(user_id, None)
        except Exception as e:
            await query.edit_message_text(f"⚠️ Ошибка: {e}")

    elif query.data == "edit_text":
        await query.edit_message_text("✏️ Введите новый текст:")
        context.user_data['editing'] = True

    elif query.data == "delete_draft":
        user_drafts.pop(user_id, None)
        await query.edit_message_text("🗑️ Черновик удалён.")

async def handle_editing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if context.user_data.get('editing'):
        if user_id not in user_drafts:
            user_drafts[user_id] = {}
        user_drafts[user_id]['text'] = update.message.text
        user_drafts[user_id]['caption'] = update.message.text
        context.user_data['editing'] = False
        await update.message.reply_text("✅ Текст обновлён.", reply_markup=get_preview_markup())

if __name__ == "__main__":
    app = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_editing))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text))
    app.add_handler(CallbackQueryHandler(handle_button))

    print("📨 PostBot запущен")
    app.run_polling()
