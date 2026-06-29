# Personal Reminder Assistant

A personal reminder backend that stores reminders in a database and sends notifications to Telegram on schedule. Supports one-time and recurring reminders (hourly, daily, weekly).

**Version:** 0.2.0

---

## Table of Contents

1. [What it does](#what-it-does)
2. [Architecture](#architecture)
3. [Project structure](#project-structure)
4. [Setup & running](#setup--running)
5. [Configuration](#configuration)
6. [Database](#database)
7. [How reminders work](#how-reminders-work)
8. [API reference](#api-reference)
9. [Timezone guide](#timezone-guide)
10. [Examples](#examples)
11. [Troubleshooting](#troubleshooting)

---

## What it does

1. You create a reminder via the REST API (title, time, optional recurrence).
2. The reminder is saved in a SQLite database.
3. A background scheduler runs inside the app and checks every 30 seconds for due reminders.
4. When a reminder is due, the app sends a message to your Telegram channel/chat.
5. One-time reminders are marked `sent`. Recurring reminders stay `pending` and reschedule to the next occurrence.

---

## Architecture

```
┌─────────────┐     HTTP      ┌──────────────────────────────────────────┐
│   Client    │ ────────────► │              FastAPI (app/main.py)        │
│ curl / docs │               │                                          │
└─────────────┘               │  ┌────────────┐    ┌──────────────────┐  │
                              │  │ Endpoints  │───►│ Services         │  │
                              │  │ (API layer)│    │ - reminder       │  │
                              │  └────────────┘    │ - telegram       │  │
                              │        │           │ - scheduler      │  │
                              │        ▼           │ - recurrence     │  │
                              │  ┌────────────┐    └────────┬─────────┘  │
                              │  │ Schemas    │             │            │
                              │  │ (validate) │             ▼            │
                              │  └────────────┘    ┌──────────────────┐  │
                              │                    │ SQLite (reminders│  │
                              │                    │ .db)             │  │
                              │                    └──────────────────┘  │
                              │                                          │
                              │  Background loop (every 30s):            │
                              │  scheduler → due reminders → Telegram  │
                              └──────────────────────────────────────────┘
                                                    │
                                                    ▼
                                         ┌──────────────────┐
                                         │  Telegram API    │
                                         │  (your channel)  │
                                         └──────────────────┘
```

### Layer responsibilities

| Layer | Folder | Purpose |
|-------|--------|---------|
| **Entry point** | `app/main.py` | Creates the FastAPI app, starts DB + scheduler on boot |
| **API routes** | `app/api/v1/endpoints/` | HTTP handlers — receive requests, return JSON |
| **Schemas** | `app/schemas/` | Request/response validation (Pydantic models) |
| **Services** | `app/services/` | Business logic — DB operations, Telegram, scheduling |
| **Models** | `app/models/` | SQLAlchemy table definitions |
| **Database** | `app/db/` | Engine, sessions, migrations |
| **Config** | `app/core/config.py` | Settings loaded from `.env` |

---

## Project structure

```
personal-reminder-assistant/
├── README.md                 # This file
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variable template
├── .env                      # Your secrets (not in git)
├── reminders.db              # SQLite database (auto-created, not in git)
└── app/
    ├── main.py               # App entry point + lifespan (scheduler)
    ├── core/
    │   └── config.py         # Settings from .env
    ├── api/
    │   ├── deps.py           # Dependency injection (DB session, Telegram)
    │   └── v1/
    │       ├── router.py     # Combines all endpoint routers
    │       └── endpoints/
    │           ├── health.py
    │           ├── hello.py
    │           ├── messages.py   # Manual Telegram send
    │           └── reminders.py  # Reminder CRUD
    ├── db/
    │   └── session.py        # DB engine, init, migrations
    ├── models/
    │   └── reminder.py       # Reminder table model
    ├── schemas/
    │   ├── reminder.py       # Reminder request/response shapes
    │   └── message.py        # Message request/response shapes
    ├── services/
    │   ├── reminder.py       # Create, list, update, cancel reminders
    │   ├── scheduler.py      # Background loop that fires due reminders
    │   ├── recurrence.py     # Hourly/daily/weekly next-time logic
    │   └── telegram.py       # Send messages via Telegram Bot API
    └── utils/
        └── datetime.py       # UTC conversion helpers
```

---

## Setup & running

### Requirements

- Python 3.10+ (3.11 recommended)
- A Telegram bot token from [@BotFather](https://t.me/BotFather)
- A Telegram channel or chat ID (bot must be admin if using a channel)

### Install

```bash
git clone https://github.com/abhijitkumar39/personal-reminder-assistant.git
cd personal-reminder-assistant

python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env and add TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID
```

### Run

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

- API docs (Swagger): http://localhost:8000/docs
- Health check: http://localhost:8000/api/v1/health

The database file (`reminders.db`) and tables are created automatically on first startup. No manual DB setup needed.

### Keep running in background

**screen:**
```bash
screen -S reminder
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
# Detach: Ctrl+A, then D
```

**systemd:** See the service example in troubleshooting or your server setup notes.

---

## Configuration

All settings go in `.env` (copy from `.env.example`):

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_NAME` | Personal Reminder Assistant | Display name |
| `APP_VERSION` | 0.2.0 | Version string |
| `DEBUG` | false | Debug mode |
| `API_V1_PREFIX` | /api/v1 | API path prefix |
| `DATABASE_URL` | sqlite:///./reminders.db | SQLite connection string |
| `SCHEDULER_INTERVAL_SECONDS` | 30 | How often to check for due reminders |
| `TELEGRAM_BOT_TOKEN` | *(required)* | Bot token from BotFather |
| `TELEGRAM_CHAT_ID` | *(required)* | Channel/chat ID (often starts with `-100`) |

---

## Database

### Engine

- **SQLite** — single file database, no separate server to install
- File location: `reminders.db` in the project root (or path from `DATABASE_URL`)
- Created automatically by `init_db()` when the app starts

### Table: `reminders`

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER | Primary key, auto-increment |
| `title` | VARCHAR(200) | Short reminder title |
| `message` | TEXT (nullable) | Longer body text (optional) |
| `remind_at` | DATETIME | Next fire time, stored as UTC |
| `recurrence` | VARCHAR(20) | `none`, `hourly`, `daily`, or `weekly` |
| `recurrence_end_at` | DATETIME (nullable) | Stop recurring after this time |
| `status` | VARCHAR(20) | `pending`, `sent`, or `cancelled` |
| `created_at` | DATETIME | When the reminder was created |
| `sent_at` | DATETIME (nullable) | When last fired (for recurring, updates each time) |

### Status lifecycle

```
                    ┌─────────────┐
         create     │   pending   │◄──── recurring reminder reschedules here
        ──────────► │             │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌───────────┐
        │   sent   │ │cancelled │ │  (fires)  │
        │ one-time │ │  DELETE  │ │ Telegram  │
        │ or ended │ │          │ │  message  │
        └──────────┘ └──────────┘ └───────────┘
```

- **pending** — waiting to fire (or will fire again if recurring)
- **sent** — one-time reminder fired, or recurring reminder reached `recurrence_end_at`
- **cancelled** — user deleted/cancelled via `DELETE /reminders/{id}`

---

## How reminders work

### Scheduler

On app startup (`app/main.py` lifespan):

1. `init_db()` — creates tables if missing, runs lightweight migrations
2. `reminder_scheduler_loop()` — background task runs forever

Every `SCHEDULER_INTERVAL_SECONDS` (default 30s):

1. Query all `pending` reminders where `remind_at <= now` (UTC)
2. For each due reminder:
   - Format message: `Reminder (every hour): Drink Water\n\nTime to hydrate!`
   - Send to Telegram
   - If **one-time** (`recurrence: none`) → set `status: sent`
   - If **recurring** → compute next `remind_at`, keep `status: pending`
   - If next time is past `recurrence_end_at` → set `status: sent`

### Recurrence

| Value | Behavior |
|-------|----------|
| `none` | Fires once, then `sent` |
| `hourly` | +1 hour from last `remind_at` |
| `daily` | +1 day from last `remind_at` |
| `weekly` | +7 days from last `remind_at` |

Example: `remind_at` at 12:40 PM with `hourly` → 12:40, 1:40, 2:40, ...

---

## API reference

Base URL: `http://YOUR_HOST:8000/api/v1`

All datetime fields in **responses** are returned in **UTC** with a `Z` suffix.

### Health & utility

#### `GET /health`

Check if the server is running.

**Response:**
```json
{
  "status": "ok",
  "version": "0.2.0"
}
```

#### `GET /hello`

Scaffold/test endpoint.

**Response:**
```json
{
  "message": "Hello, World!"
}
```

---

### Messages (manual Telegram send)

#### `POST /messages`

Send a message to Telegram immediately (not scheduled).

**Request body:**
```json
{
  "message": "Hello from the API!"
}
```

| Field | Type | Required | Rules |
|-------|------|----------|-------|
| `message` | string | yes | 1–4096 characters |

**Response (200):**
```json
{
  "success": true,
  "message_id": 12345
}
```

**Errors:**
- `503` — Telegram token or chat ID not configured
- `502` — Telegram API error

---

### Reminders

#### `POST /reminders`

Create a new reminder.

**Request body:**
```json
{
  "title": "Drink Water",
  "message": "Time to hydrate!",
  "remind_at": "2026-06-29T12:40:00+05:30",
  "recurrence": "hourly",
  "recurrence_end_at": null
}
```

| Field | Type | Required | Default | Rules |
|-------|------|----------|---------|-------|
| `title` | string | yes | — | 1–200 characters |
| `message` | string | no | null | Max 4096 characters |
| `remind_at` | datetime | yes | — | Must be in the future |
| `recurrence` | string | no | `none` | `none`, `hourly`, `daily`, `weekly` |
| `recurrence_end_at` | datetime | no | null | Only for recurring; must be after `remind_at` |

**Response (201):**
```json
{
  "id": 1,
  "title": "Drink Water",
  "message": "Time to hydrate!",
  "remind_at": "2026-06-29T07:10:00Z",
  "recurrence": "hourly",
  "recurrence_end_at": null,
  "status": "pending",
  "created_at": "2026-06-29T06:54:49.970975Z",
  "sent_at": null
}
```

---

#### `GET /reminders`

List reminders, filtered by status.

**Query parameters:**

| Param | Type | Default | Values |
|-------|------|---------|--------|
| `status` | string | `pending` | `pending`, `sent`, `cancelled` |

**Example:** `GET /reminders?status=pending`

**Response (200):** Array of reminder objects (same shape as create response).

---

#### `GET /reminders/{id}`

Get a single reminder by ID.

**Response (200):** Reminder object.

**Errors:**
- `404` — Reminder not found

---

#### `PATCH /reminders/{id}`

Update a pending reminder. All fields are optional — only send what you want to change.

**Request body (example):**
```json
{
  "remind_at": "2026-06-29T12:40:00+05:30"
}
```

| Field | Type | Rules |
|-------|------|-------|
| `title` | string | 1–200 characters |
| `message` | string | Max 4096 characters |
| `remind_at` | datetime | Must be in the future |
| `recurrence` | string | `none`, `hourly`, `daily`, `weekly` |
| `recurrence_end_at` | datetime | Must be in the future |

**Response (200):** Updated reminder object.

**Errors:**
- `404` — Reminder not found
- `409` — Only `pending` reminders can be updated
- `422` — Validation error (e.g. time in the past)

---

#### `DELETE /reminders/{id}`

Cancel a pending reminder (sets `status` to `cancelled`).

**Response (200):** Cancelled reminder object.

**Errors:**
- `404` — Reminder not found
- `409` — Only `pending` reminders can be cancelled

---

## Timezone guide

**Important:** Always include a timezone offset when creating or updating reminders.

| You send | Meaning |
|----------|---------|
| `2026-06-29T12:40:00+05:30` | 12:40 PM India time (IST) |
| `2026-06-29T07:10:00Z` | Same moment in UTC |
| `2026-06-29T12:40:00` *(no offset)* | Treated as UTC — probably not what you want |

**API responses** always return UTC with `Z`:
```json
"remind_at": "2026-06-29T07:10:00Z"
```

To convert: **IST = UTC + 5:30**

---

## Examples

### One-time reminder

```bash
curl -X POST http://192.168.1.26:8000/api/v1/reminders \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Call mom",
    "message": "Birthday call",
    "remind_at": "2026-06-30T18:00:00+05:30",
    "recurrence": "none"
  }'
```

### Hourly — drink water at :40 every hour

```bash
curl -X POST http://192.168.1.26:8000/api/v1/reminders \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Drink Water",
    "message": "Time to hydrate!",
    "remind_at": "2026-06-29T12:40:00+05:30",
    "recurrence": "hourly"
  }'
```

### Daily — vitamins at 9 AM

```bash
curl -X POST http://192.168.1.26:8000/api/v1/reminders \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Take vitamins",
    "remind_at": "2026-06-30T09:00:00+05:30",
    "recurrence": "daily"
  }'
```

### Weekly — review goals every Monday 10 AM for 3 months

```bash
curl -X POST http://192.168.1.26:8000/api/v1/reminders \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Review goals",
    "remind_at": "2026-06-30T10:00:00+05:30",
    "recurrence": "weekly",
    "recurrence_end_at": "2026-09-30T10:00:00+05:30"
  }'
```

### List all pending reminders

```bash
curl http://192.168.1.26:8000/api/v1/reminders
```

### Cancel a reminder

```bash
curl -X DELETE http://192.168.1.26:8000/api/v1/reminders/1
```

### Snooze — push reminder 30 minutes later

```bash
curl -X PATCH http://192.168.1.26:8000/api/v1/reminders/1 \
  -H "Content-Type: application/json" \
  -d '{
    "remind_at": "2026-06-29T13:10:00+05:30"
  }'
```

---

## Troubleshooting

### Reminder didn't fire

1. Is the server running? `curl http://localhost:8000/api/v1/health`
2. Is `status` still `pending`? `GET /reminders/1`
3. Is `remind_at` in the past (UTC)? Check the `Z` time in the response
4. Are Telegram credentials set in `.env`?
5. Scheduler checks every 30s — message may arrive up to 30s after the scheduled time

### Telegram errors

| Error | Fix |
|-------|-----|
| `503` — token/chat not configured | Set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in `.env` |
| `403 Forbidden` | Bot not added as channel admin |
| `400 Bad Request: chat not found` | Wrong `TELEGRAM_CHAT_ID` |

### Getting Telegram chat ID

1. Add your bot to the channel as admin
2. Send a message in the channel
3. Visit: `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
4. Look for `"chat":{"id":-100...}`

### Python version error (`str | None`)

Requires Python 3.10+. Check with `python3 --version`. Upgrade or recreate venv with 3.11.

### After `git pull`

```bash
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
# Restart uvicorn or systemctl restart reminder-assistant
```

---

## What's not built yet (future ideas)

- Telegram bot commands (`/remind me in 1h`)
- Natural language time parsing ("tomorrow at 9am")
- API authentication
- Web UI
- Snooze as a dedicated endpoint
- Multiple users / chat IDs
