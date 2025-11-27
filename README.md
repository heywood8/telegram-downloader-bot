# Telegram Downloader Bot

This is a minimal bot that replies "Here you go" when a message contains an Instagram link.

Quickstart

1. Copy `.env.example` to `env/.env` and set your token:

```bash
mkdir -p env
cp .env.example env/.env
# Edit env/.env and set your TELEGRAM_BOT_TOKEN
```

2. Install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

3. Run the bot:

```bash
python3 bot.py
```

Notes

- This bot uses polling. For production, consider running under systemd or as a container and secure the token.
- If you want different behavior (replying with the matched URL, localization, or filters), open an issue or update `bot.py`.

## Configuration

You can enable/disable the HTTP test server and Telegram polling via environment variables in `env/.env`:

```
ENABLE_HTTP_SERVER=true      # Enable HTTP server on port 8080 (default: true)
ENABLE_TELEGRAM_POLLING=true # Enable Telegram polling (default: true)
TELEGRAM_BOT_TOKEN=<your-token-here>
```

- Set to `false`, `0`, or `no` to disable either feature.
- If both are disabled, the bot will not run any service.

## Example: HTTP-only mode

```
ENABLE_HTTP_SERVER=true
ENABLE_TELEGRAM_POLLING=false
```

Then run:

```bash
python3 bot.py
```

Test with:

```bash
curl -X POST http://localhost:8080/update -H "Content-Type: application/json" -d '{"message": "https://instagram.com/test"}'
```
