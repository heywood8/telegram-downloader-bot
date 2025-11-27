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
from dotenv import load_dotenv
from aiohttp import web
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

INSTAGRAM_RE = re.compile(r'(?:(?:https?://)?(?:www\.)?(?:instagram\.com|instagr\.am)/\S+)', flags=re.IGNORECASE)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Hi! Send an Instagram link and I'll reply.")


def check_instagram_link(text: str) -> bool:
    return bool(INSTAGRAM_RE.search(text or ""))


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (update.message.text or "")
    try:
        if check_instagram_link(text):
            await update.message.reply_text("Here you go")
            logger.info("Replied to Instagram link", extra={"chat_id": update.effective_chat.id, "user": getattr(update.effective_user, 'username', None)})
    except Exception as e:
        logger.exception("Error in handle_message: %s", e)


# HTTP endpoint for testing
async def http_update(request):
    try:
        try:
            data = await request.json()
        except Exception as e:
            logger.warning(f"Invalid JSON in /update: {e}")
            return web.json_response({"reply": "Invalid JSON"}, status=400)
        text = data.get("message")
        if not text:
            logger.info("No 'message' field in /update request")
            return web.json_response({"reply": "No message"}, status=400)
        logger.info(f"Received HTTP update: {text}")
        if check_instagram_link(text):
            reply = "Here you go"
        else:
            reply = "No Instagram link detected"
        return web.json_response({"reply": reply})
    except Exception as e:
        logger.exception("Error in /update endpoint: %s", e)
        return web.json_response({"error": str(e)}, status=400)


def get_bool_env(varname: str, default: bool = True) -> bool:
    val = os.environ.get(varname)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


def main() -> None:
    # Load environment variables from env/.env
    load_dotenv('env/.env')
    
    enable_http = get_bool_env('ENABLE_HTTP_SERVER', True)
    enable_telegram = get_bool_env('ENABLE_TELEGRAM_POLLING', True)

    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if enable_telegram and not token:
        logger.error('Environment variable TELEGRAM_BOT_TOKEN is not set')
        raise SystemExit('Set TELEGRAM_BOT_TOKEN and try again')

    app = None
    if enable_telegram:
        app = Application.builder().token(token).build()
        app.add_handler(CommandHandler('start', start))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    async def run_http_server():
        http_app = web.Application()
        http_app.router.add_post('/update', http_update)
        runner = web.AppRunner(http_app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', 8080)
        logger.info("HTTP test server running on http://0.0.0.0:8080/update")
        await site.start()
        while True:
            await asyncio.sleep(3600)

    async def run_telegram():
        logger.info('Starting Telegram downloader bot (polling)...')
        bot_info = await app.bot.get_me()
        logger.info(f"Bot username: {bot_info.username}, name: {bot_info.first_name}")
        await app.initialize()
        app.run_polling(allowed_updates=["message", "edited_message"], drop_pending_updates=True)

    async def run_all():
        tasks = []
        if enable_telegram:
            tasks.append(asyncio.create_task(run_telegram()))
        if enable_http:
            tasks.append(asyncio.create_task(run_http_server()))
        if not tasks:
            logger.error("Both HTTP server and Telegram polling are disabled. Nothing to run.")
            return
        await asyncio.gather(*tasks)

    try:
        asyncio.run(run_all())
    except KeyboardInterrupt:
        logger.info('Shutting down')


if __name__ == '__main__':
    main()
