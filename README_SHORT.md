# MarketWatcher — Quick Start

## 1. Create and activate virtual environment

```bash
cd /Volumes/MacData/python/MarketWatcher

/usr/local/bin/python3.11 -m venv .venv
source .venv/bin/activate
```

Your prompt will show `(.venv)` when active. Run `source .venv/bin/activate` every new terminal session.

## 2. Install dependencies

```bash
pip install -e .
playwright install chromium
```

## 3. Configure

```bash
cp config.example.yaml config.yaml
```

Edit `config.yaml`:
- `telegram.bot_token` — from @BotFather
- `telegram.chat_id` — numeric ID from @userinfobot
- `openai.api_key` — your OpenAI key (set `enabled: false` to skip AI verdicts)
- `watches` — your search URLs and max prices

## 4. First run — log in to Facebook

Set `headless: false` in config.yaml, then:

```bash
python -m marketwatcher.main --config config.yaml --once
```

A browser window opens. Log into Facebook. Session saves to `data/browser_state.json`. After this you can set `headless: true`.

## 5. Run

**Scan once:**
```bash
python -m marketwatcher.main --config config.yaml --once
```

**Run continuously** (every 15 minutes by default):
```bash
python -m marketwatcher.main --config config.yaml --loop
```

**Debug mode:**
```bash
python -m marketwatcher.main --config config.yaml --once --debug
```

Stop with `Ctrl+C` — state is saved cleanly on exit.

## 6. Manage seen listings

**List watches and remembered listing counts:**
```bash
python -m marketwatcher.main --config config.yaml --list-watches
```

**Clear memory for one watch** (will re-notify all current matches on next run):
```bash
python -m marketwatcher.main --config config.yaml --clear-watch "Toyota Prius"
```

**Clear everything:**
```bash
echo '{"seen": []}' > data/seen_listings.json
```

## Notes

- Seen listings are tracked in `data/seen_listings.json` — no duplicate notifications across restarts
- AI verdict is fetched from ChatGPT for every match and included in the Telegram message
- Logs are written to `logs/marketwatcher.log`
- If the Facebook session expires, delete `data/browser_state.json` and repeat step 4
- `config.yaml` contains credentials — never commit it to git
