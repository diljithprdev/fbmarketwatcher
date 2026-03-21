# MarketWatcher

Monitor Facebook Marketplace search results and get Telegram alerts the moment a listing appears within your price range. Each alert includes an AI verdict from ChatGPT on whether the price is below market value.

---

## What it does

You tell MarketWatcher what you are looking for, how much you are willing to pay, and which words must or must not appear in the listing. It opens Marketplace in a browser, reads the search results, fetches each matching listing's description, asks ChatGPT if it is a good deal, and sends you a Telegram message. Run it once manually or leave it running in the background on a schedule.

---

## Prerequisites

| Requirement | Notes |
|---|---|
| Python 3.11 or newer | Check with `python --version` |
| A Facebook account | Must have Marketplace access in your region |
| A Telegram bot | Free — takes two minutes to create (see below) |
| An OpenAI API key | For AI verdicts — optional, disable with `enabled: false` |

---

## Step 1 — Create a Telegram bot

You only need to do this once.

1. Open Telegram and search for **@BotFather**.
2. Send `/newbot` and follow the prompts.
3. BotFather replies with a **bot token** like `123456789:ABCdef...`. Copy it.
4. To find your **chat ID**: search for **@userinfobot** in Telegram, start a chat, it replies with your numeric ID.
5. Send any message to your new bot (e.g. `/start`) — required before it can message you.

---

## Step 2 — Install MarketWatcher

```bash
# From the project directory, create a virtual environment with Python 3.11
/usr/local/bin/python3.11 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e .
playwright install chromium
```

The `playwright install chromium` command downloads the browser MarketWatcher controls (~150 MB, one-time only).

---

## Step 3 — Create your config file

```bash
cp config.example.yaml config.yaml
```

Open `config.yaml` and fill in the four sections:

### Telegram section

```yaml
telegram:
  bot_token: "123456789:YOUR_BOT_TOKEN"
  chat_id: "123456789"       # your numeric ID from @userinfobot
  enabled: true
```

### Scanner section

```yaml
scanner:
  headless: false              # false = visible browser window (needed for first login)
  scan_interval_seconds: 900   # how often to scan in loop mode (900 = 15 minutes)
  page_load_timeout_ms: 45000
  post_load_wait_ms: 3000
  max_listings_per_watch: 50
  storage_state_path: "data/browser_state.json"
```

### OpenAI section

```yaml
openai:
  api_key: "sk-proj-..."
  org_id: "org-..."            # optional
  model: "gpt-4o-mini"         # cheap and fast; use gpt-4o for deeper analysis
  enabled: true                # set false to disable AI verdicts
```

### Watches section

Each watch is one search to monitor. Add as many as you like.

```yaml
watches:
  - name: "iphone 13"
    enabled: true                        # set false to pause without deleting
    marketplace_url: "https://www.facebook.com/marketplace/london/search?query=iphone+13"
    max_price: 300
    notify_on_free: true
    currency: "GBP"
    keywords_include:                    # ALL must appear in the listing
      - "iphone"
      - "13"
    keywords_exclude:                    # ANY of these discards the listing
      - "case"
      - "repair"
```

**How to get the right Marketplace URL:**
1. Go to `facebook.com/marketplace` in your browser.
2. Search for your item and apply location/category filters.
3. Copy the full URL from the address bar.

---

## Step 4 — Log in to Facebook (first run only)

Make sure `headless: false` is set in your config, then run:

```bash
python -m marketwatcher.main --config config.yaml --once
```

A Chromium window opens. Log into Facebook manually. The session saves to `data/browser_state.json` and is reused on all future runs. Once logged in you can set `headless: true`.

---

## Step 5 — Run MarketWatcher

**Scan once and exit:**
```bash
python -m marketwatcher.main --config config.yaml --once
```

**Run continuously** (repeats every `scan_interval_seconds`):
```bash
python -m marketwatcher.main --config config.yaml --loop
```

**Debug mode** (verbose output for every listing parsed):
```bash
python -m marketwatcher.main --config config.yaml --once --debug
```

Stop with `Ctrl+C` — state is saved cleanly on exit.

---

## Step 6 — Manage seen listings

MarketWatcher remembers every listing it has already notified so you never get duplicates.

**List all watches and how many listings are remembered:**
```bash
python -m marketwatcher.main --config config.yaml --list-watches
```

**Clear memory for one watch** (next run will re-notify all current matches for that watch):
```bash
python -m marketwatcher.main --config config.yaml --clear-watch "iphone 13"
```

**Clear everything:**
```bash
echo '{"seen": []}' > data/seen_listings.json
```

These commands exit immediately — no browser is launched.

---

## What a Telegram alert looks like

```
MarketWatcher match found
Watch: iphone 13
Title: iPhone 13 128GB Blue
Price: £280
Location: Manchester
URL: https://www.facebook.com/marketplace/item/1234567890/

AI Verdict: At £280 this is well below the typical UK market price
of £350–£450 for a 128GB iPhone 13 in good condition. Worth
pursuing — verify the condition and ask for photos.
```

For a free listing:

```
MarketWatcher FREE match found
Watch: office chair
Title: Ergonomic Office Chair
Price: FREE
Location: Salford
URL: https://www.facebook.com/marketplace/item/9876543210/

AI Verdict: A free ergonomic office chair is an excellent deal —
these typically sell for £50–£200 secondhand. Collect quickly as
free items go fast.
```

If OpenAI is disabled or fails, the notification still sends without the verdict.

---

## How matching works

A listing triggers a notification only when **all** of these are true:

1. It has not been notified before (checked against `data/seen_listings.json`).
2. The watch it belongs to is enabled.
3. Every word in `keywords_include` appears in the listing text.
4. No word in `keywords_exclude` appears in the listing text.
5. Either the price is at or below `max_price`, or the listing is FREE and `notify_on_free` is true.

Keywords are case-insensitive.

---

## Logs

Logs are written to both the terminal and `logs/marketwatcher.log`. The file rotates at 5 MB and keeps 3 backups.

```
2026-03-21 14:00:01  INFO     Loaded config from config.yaml
2026-03-21 14:00:02  INFO     Browser started (headless=True)
2026-03-21 14:00:03  INFO     Running watch: iphone 13
2026-03-21 14:00:08  INFO     Parsed 32 listings for watch iphone 13
2026-03-21 14:00:08  INFO     Match found: iPhone 13 128GB Blue | £280 GBP
2026-03-21 14:00:09  INFO     AI verdict for listing 1234567890: At £280 this is well below...
2026-03-21 14:00:09  INFO     Notification sent for listing 1234567890
2026-03-21 14:00:09  INFO     Scan cycle complete
```

---

## Running on a schedule with cron (optional)

```
*/15 * * * * cd /path/to/MarketWatcher && source .venv/bin/activate && python -m marketwatcher.main --config config.yaml --once >> logs/cron.log 2>&1
```

---

## Troubleshooting

**No listings are found**
- Facebook may have changed its page structure. Run with `headless: false` and `--debug` to watch the browser.
- Your session may have expired. Delete `data/browser_state.json` and repeat Step 4.

**Listings are found but no matches fire**
- Run with `--debug` to see price parsing and keyword filter results for each listing.
- The price format on the page may not be recognised — check `parser.py:_parse_price`.

**Telegram messages are not arriving**
- Make sure you have sent at least one message to your bot first (`/start`).
- Verify `bot_token` and `chat_id` in `config.yaml` — get your real chat ID from @userinfobot, not from the bot token.
- Check `logs/marketwatcher.log` for 403/4xx errors.

**AI verdict is missing from notifications**
- Check `logs/marketwatcher.log` for OpenAI errors.
- Verify your `api_key` and `org_id` in `config.yaml`.
- Set `enabled: false` under `openai:` to disable without removing the config.

**Session keeps expiring**
- Facebook sessions typically last weeks. When expired you will see 0 listings parsed. Delete `data/browser_state.json` and repeat Step 4.

---

## Project layout

```
MarketWatcher/
├── config.yaml              your config — do not commit (contains credentials)
├── config.example.yaml      safe template for new setups
├── pyproject.toml           package definition
├── requirements.txt
├── .gitignore
├── README.md
├── README_SHORT.md          quick-start reference
├── HANDOFF.md               context document for continuing development
├── data/
│   ├── seen_listings.json   remembered listing IDs — auto-created
│   └── browser_state.json   Facebook login session — created after first login
├── logs/
│   └── marketwatcher.log    rotating log file
└── src/marketwatcher/
    ├── main.py              CLI entry point
    ├── config.py            YAML config loader
    ├── models.py            Pydantic config models + Listing dataclass
    ├── marketplace.py       Playwright browser control + description fetching
    ├── parser.py            listing extraction, price parsing, keyword matching
    ├── analyzer.py          ChatGPT market value analysis
    ├── notifier.py          Telegram alert formatting and sending
    ├── state.py             seen-listing persistence and watch management
    ├── runner.py            scan cycle orchestration
    └── logger.py            logging setup
```
