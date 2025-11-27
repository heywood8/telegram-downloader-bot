#!/usr/bin/env python3
"""Minimal Telegram bot that replies "Here you go" to Instagram links.

Usage:
- Set `TELEGRAM_BOT_TOKEN` environment variable to your bot token.
- Run: `python3 telegram-downloader-bot/bot.py`

This bot uses long polling and the `python-telegram-bot` v20+ API.
"""

import os
import re
import logging
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

INSTAGRAM_RE = re.compile(r'(?:(?:https?://)?(?:www\.)?(?:instagram\.com|instagr\.am)/\S+)', flags=re.IGNORECASE)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Hi! Send an Instagram link and I'll reply.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (update.message.text or "")
    try:
        if INSTAGRAM_RE.search(text):
            await update.message.reply_text("Here you go")
            logger.info("Replied to Instagram link", extra={"chat_id": update.effective_chat.id, "user": getattr(update.effective_user, 'username', None)})
    except Exception as e:
        logger.exception("Error in handle_message: %s", e)


def main() -> None:
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if not token:
        logger.error('Environment variable TELEGRAM_BOT_TOKEN is not set')
        raise SystemExit('Set TELEGRAM_BOT_TOKEN and try again')

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler('start', start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info('Starting Telegram downloader bot (polling)...')
    try:
        app.run_polling(allowed_updates=["message", "edited_message"], drop_pending_updates=True)
    except KeyboardInterrupt:
        logger.info('Shutting down')


if __name__ == '__main__':
    main()
