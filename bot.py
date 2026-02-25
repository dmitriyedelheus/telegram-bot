"""
Телеграм-бот: принимает скриншоты и сообщения от пользователей и пересылает их вам.
"""
import asyncio
import os
import sys
import logging

# Python 3.14+ больше не создаёт event loop автоматически
if sys.version_info >= (3, 14):
    asyncio.set_event_loop(asyncio.new_event_loop())
from dotenv import load_dotenv

load_dotenv()
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, ContextTypes, filters

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
# Список chat ID админов (через запятую в .env)
ADMIN_CHAT_IDS = [
    aid.strip()
    for aid in (os.environ.get("ADMIN_CHAT_ID") or "").split(",")
    if aid.strip()
]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка команды /start."""
    await update.message.reply_text(
        "Привет! Отправь скриншот или сообщение — они будут доставлены владельцу бота."
    )


async def forward_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Пересылает любое сообщение (текст, фото, видео, голос и т.д.) всем админам."""
    if not ADMIN_CHAT_IDS:
        logger.error("ADMIN_CHAT_ID не задан")
        return

    delivered = 0
    errors = []

    user = update.effective_user
    sender = f"@{user.username}" if user.username else (user.first_name or "Пользователь")

    for chat_id in ADMIN_CHAT_IDS:
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"От: {sender}",
            )
            await context.bot.forward_message(
                chat_id=chat_id,
                from_chat_id=update.effective_chat.id,
                message_id=update.message.message_id,
            )
            delivered += 1
        except Exception as e:
            logger.warning("Не удалось переслать в %s: %s", chat_id, e)
            errors.append(f"{chat_id}: {e!s}")

    if delivered > 0:
        await update.message.reply_text("✓ Доставлено!")
    else:
        logger.error("Не доставлено ни одному админу: %s", errors)
        await update.message.reply_text(
            "Не удалось отправить. Попробуйте позже."
        )


async def get_my_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет chat ID пользователя (для настройки ADMIN_CHAT_ID)."""
    chat_id = update.effective_chat.id
    await update.message.reply_text(f"Ваш chat ID: `{chat_id}`", parse_mode="Markdown")


def main() -> None:
    if not BOT_TOKEN:
        raise SystemExit("Задайте переменную окружения TELEGRAM_BOT_TOKEN")
    if not ADMIN_CHAT_IDS:
        logger.warning(
            "ADMIN_CHAT_ID не задан. Запустите бота и отправьте /myid, чтобы узнать chat ID."
        )

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("myid", get_my_id))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, forward_message))

    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
