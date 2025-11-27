# Telegram Downloader Bot

This is a minimal bot that replies "Here you go" when a message contains an Instagram link.

Quickstart

1. Create a bot via BotFather and get the `TELEGRAM_BOT_TOKEN`.
2. Create `env/.env` file with your token:

```bash
mkdir -p env
echo "TELEGRAM_BOT_TOKEN=<your-token-here>" > env/.env
```

3. Install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

4. Run the bot:

```bash
python3 bot.py
```

Notes

- This bot uses polling. For production, consider running under systemd or as a container and secure the token.
- If you want different behavior (replying with the matched URL, localization, or filters), open an issue or update `bot.py`.
