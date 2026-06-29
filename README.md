# PROSTO — Siege of Leningrad event bot

A Telegram bot built for the St. Petersburg state institution **GBU «PROSTO»**
([prostospb.team](https://www.prostospb.team/)) as part of the campaign marking
the anniversary of the **lifting of the Siege of Leningrad**.

Visitors take a short historical **quiz**, leave their contact details to take
part in the event, and an administrator can export all responses to an Excel
report.

## Features

- 8-question quiz on the history of the Siege of Leningrad (`quiz_questions.json`)
- Collects participant details (name, phone) into a local SQLite database
- One-tap phone sharing via Telegram's contact button
- Admin tools: view participants, delete a record, and **export everything to
  `.xlsx`** with timestamps in Moscow time
- Self-healing schema — missing columns are added on startup

## Requirements

- Python 3.10+
- A bot token from [@BotFather](https://t.me/BotFather)

## Setup

```bash
git clone https://github.com/dayanegosha/PROSTO-siege-event-bot.git
cd PROSTO-siege-event-bot

python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run

Both the token and the admin id are read from the environment — nothing is
hardcoded:

```bash
export BOT_TOKEN="123456:your-token-here"   # from @BotFather
export ADMIN_ID="123456789"                 # your Telegram user id
python main.py
```

The bot creates `users_data.db` on first run. That file holds participants'
personal data and is git-ignored — keep it out of version control.

## Project layout

```
PROSTO-siege-event-bot/
├── main.py              # bot logic, quiz flow, admin panel, xlsx export
├── quiz_questions.json  # quiz questions, options and correct answers
├── requirements.txt
└── README.md
```

## License

[MIT](LICENSE) © George Zhurik
