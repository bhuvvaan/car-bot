# Car Bot

A Telegram bot that lets you control and query a Hyundai/Kia vehicle in natural language. Uses Claude for tool calling and the `hyundai_kia_connect_api` library to interact with Bluelink.

## What it does

Send messages like:
- "Is my car charged?"
- "Lock the doors"
- "Where is my car?"
- "Turn on climate at 72 degrees"
- "Stop charging"

Claude interprets your message, calls the right Bluelink API, and replies in natural language.

## Architecture

You (Telegram)
→ python-telegram-bot
→ Claude API (with tool definitions)
→ hyundai_kia_connect_api
→ Hyundai Bluelink servers
→ response back through the chain

## Setup

### Prerequisites

- Python 3.10+
- A Hyundai or Kia vehicle with active Bluelink subscription
- Telegram account
- Anthropic API key

### Local installation

1. Clone the repo:
```bash
git clone https://github.com/bhuvvaan/car-bot.git
cd car-bot
```

2. Create a virtual environment:
```bash
python3 -m venv env
source env/bin/activate  # On Windows: env\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Get your credentials:
   - **Telegram bot token**: Message [@BotFather](https://t.me/BotFather), use `/newbot`
   - **Your Telegram chat ID**: Send your bot a message, then visit `https://api.telegram.org/bot<TOKEN>/getUpdates` to find your chat ID
   - **Anthropic API key**: Get from [console.anthropic.com](https://console.anthropic.com)
   - **Bluelink credentials**: Your existing Hyundai Bluelink email, password, and PIN

5. Create `.env` file:
```bash
cp .env.example .env
nano .env  # Fill in your credentials
```

6. Run the bot:
```bash
python bot.py
```

Send a message to your bot on Telegram.

### Production deployment

The bot runs as a systemd service on a VPS for 24/7 operation.

1. SSH into your server
2. Clone the repo and follow setup steps above
3. Create the systemd service:

```bash
sudo nano /etc/systemd/system/car-bot.service
```

```ini
[Unit]
Description=Car Bot Telegram Service
After=network.target

[Service]
Type=simple
User=yourusername
WorkingDirectory=/home/yourusername/car-bot
Environment="PATH=/home/yourusername/car-bot/env/bin"
ExecStart=/home/yourusername/car-bot/env/bin/python bot.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

4. Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable car-bot
sudo systemctl start car-bot
sudo systemctl status car-bot
```

5. View logs:
```bash
sudo journalctl -u car-bot -f
```

## Project structure

car-bot/
├── bot.py              # Telegram message handler entry point
├── car.py              # Bluelink API integration and tool functions
├── claude.py           # Claude API integration and tool routing
├── tools.py            # Tool definitions for Claude
├── requirements.txt    # Python dependencies
├── .env.example        # Template for environment variables
└── README.md

## Region codes

In `.env`, set `BLUELINK_REGION` based on your location:
- `1` = Europe
- `2` = Canada
- `3` = USA
- `4` = Korea

And `BLUELINK_BRAND`:
- `1` = Kia
- `2` = Hyundai
- `3` = Genesis

## Security

- Bot only responds to your specific Telegram chat ID (whitelist)
- All credentials stored in `.env` (gitignored)
- Runs as non-root user on production server
- SSH key authentication only

## Notes

- The `hyundai_kia_connect_api` library is reverse-engineered, not officially supported by Hyundai
- API can be unreliable; commands sometimes need a retry
- Tested on a 2024 Hyundai Ioniq 5 in the USA region
- Climate control responses are best-effort due to API quirks

## Acknowledgments

- [hyundai_kia_connect_api](https://github.com/Hyundai-Kia-Connect/hyundai_kia_connect_api) for the Bluelink integration
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) for Telegram handling
- [Anthropic](https://anthropic.com) for Claude API

## License

MIT (or whatever you prefer)