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
import http.client
import signal
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


def extract_reel_id(url: str) -> str:
    """
    Extract the reel ID from a given Instagram URL.

    Args:
        url (str): The Instagram URL containing the reel ID.

    Returns:
        str: The extracted reel ID, or an empty string if not found.
    """
    match = re.search(r"/reel/([\w-]+)/", url)
    if match:
        return match.group(1)
    return ""


def get_bool_env(varname: str, default: bool = True) -> bool:
    val = os.environ.get(varname)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


async def fetch_reel_data(reel_id: str, rapid_api_key: str) -> str:
    """
    Fetch reel data from RapidAPI using the provided reel ID.

    Args:
        reel_id (str): The Instagram reel ID.
        rapid_api_key (str): The RapidAPI key for authentication.

    Returns:
        str: The extracted URL from the API response.
    """
    conn = http.client.HTTPSConnection("instagram120.p.rapidapi.com")

    payload = json.dumps({"shortcode": reel_id})

    headers = {
        'x-rapidapi-key': rapid_api_key,
        'x-rapidapi-host': "instagram120.p.rapidapi.com",
        'Content-Type': "application/json"
    }

    conn.request("POST", "/api/instagram/mediaByShortcode", payload, headers)

    res = conn.getresponse()
    data = res.read()

    try:
        logger.debug(f"Raw API response: {data}")
        response_json = json.loads(data)
        logger.debug(f"Decoded JSON response: {response_json}")

        # Directly access the first URL in the response structure
        first_url = response_json[0]["urls"][0]["url"]
        return first_url
    except json.JSONDecodeError:
        logger.error("Failed to decode JSON response from RapidAPI")
        return "Error decoding API response"
    except KeyError as e:
        logger.exception("Missing expected key in API response: %s", e)
        return "Error processing API response"
    except Exception as e:
        logger.exception("Unexpected error while processing API response: %s", e)
        return "Error processing API response"


async def process_instagram_link(text: str) -> str:
    """
    Process an Instagram link to extract the reel ID and fetch data from RapidAPI.

    Args:
        text (str): The message text containing the Instagram link.

    Returns:
        str: The response message to be sent back.
    """
    rapid_api_key = os.environ.get('RAPID_API_KEY')
    if not rapid_api_key:
        return "RapidAPI key is not configured."

    if not check_instagram_link(text):
        return "No Instagram link detected"

    reel_id = extract_reel_id(text)
    if not reel_id:
        return "Reel ID not found"

    try:
        api_response = await fetch_reel_data(reel_id, rapid_api_key)
        return f"Extracted URL: {api_response}"
    except Exception as e:
        logger.exception("Error fetching data from RapidAPI: %s", e)
        return "Error fetching data from RapidAPI"


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (update.message.text or "")
    try:
        reply = await process_instagram_link(text)
        await update.message.reply_text(reply)
        logger.info("Replied to Instagram link", extra={"chat_id": update.effective_chat.id, "user": getattr(update.effective_user, 'username', None)})
    except Exception as e:
        logger.exception("Error in handle_message: %s", e)


# HTTP endpoint for testing
async def http_update(request):
    try:
        data = await request.json()
    except json.JSONDecodeError as e:
        logger.warning(f"Invalid JSON in /update: {e}")
        return web.json_response({"reply": "Invalid JSON"}, status=400)
    except Exception as e:
        logger.exception("Unexpected error while parsing JSON: %s", e)
        return web.json_response({"reply": "Error while parsing JSON"}, status=500)

    text = data.get("message")
    if not text:
        logger.info("No 'message' field in /update request")
        return web.json_response({"reply": "No message"}, status=422)

    logger.info(f"Received HTTP update: {text}")

    reply = await process_instagram_link(text)
    return web.json_response({"reply": reply})


def main() -> None:
    # Load environment variables from env/.env
    load_dotenv('env/.env')

    enable_http = get_bool_env('ENABLE_HTTP_SERVER', True)
    enable_telegram = get_bool_env('ENABLE_TELEGRAM_POLLING', True)

    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if enable_telegram and not token:
        logger.error('Environment variable TELEGRAM_BOT_TOKEN is not set')
        raise SystemExit('Set TELEGRAM_BOT_TOKEN and try again')

    rapid_api_key = os.environ.get('RAPID_API_KEY')
    if not rapid_api_key:
        logger.error('Environment variable RAPID_API_KEY is not set')
        raise SystemExit('Set RAPID_API_KEY and try again')

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
        await app.start()

        # Send startup notification (if needed)
        logger.info("Bot is running! Press Ctrl+C to stop.")

        # Keep the bot running until a shutdown signal is received
        stop_event = asyncio.Event()

        def signal_handler(sig, frame):
            logger.info("Received shutdown signal")
            stop_event.set()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        await stop_event.wait()

        # Shutdown logic
        logger.info("Stopping the application...")
        await app.updater.stop()
        await app.stop()
        await app.shutdown()

    async def run_all():
        tasks = []
        if enable_telegram:
            tasks.append(asyncio.create_task(run_telegram()))
        if enable_http:
            tasks.append(asyncio.create_task(run_http_server()))
        if not tasks:
            logger.error("Both HTTP server and Telegram polling are disabled. Nothing to run.")
            return

        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.exception("An error occurred while running tasks: %s", e)
        finally:
            logger.info("Shutting down all tasks.")

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            logger.warning("Event loop is already running. Using create_task instead of asyncio.run.")
            loop.create_task(run_all())
        else:
            asyncio.run(run_all())
    except KeyboardInterrupt:
        logger.info('Shutting down')


if __name__ == '__main__':
    main()
