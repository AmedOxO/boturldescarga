from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from config import BOT_TOKEN, TARGET_CHAT_ID
from utils import start_msg, error_msg

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(start_msg)

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if TARGET_CHAT_ID is None:
        await update.message.reply_text("⚠️ No hay destino configurado en config.py")
        return

    file_obj = None
    send_func = None

    if update.message.document:
        file_obj = update.message.document.file_id
        send_func = context.bot.send_document
    elif update.message.photo:
        file_obj = update.message.photo[-1].file_id
        send_func = context.bot.send_photo
    elif update.message.video:
        file_obj = update.message.video.file_id
        send_func = context.bot.send_video
    elif update.message.audio:
        file_obj = update.message.audio.file_id
        send_func = context.bot.send_audio
    else:
        await update.message.reply_text("❌ Archivo no soportado")
        return

    try:
        await send_func(chat_id=TARGET_CHAT_ID, file=file_obj, caption="☁️ Archivo guardado en tu nube")
        await update.message.reply_text("✅ Subido correctamente")
    except Exception as e:
        await update.message.reply_text(error_msg + str(e))

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.ALL, handle_file))
    print("🤖 Bot activo...")
    app.run_polling()

if __name__ == "__main__":
    main()
