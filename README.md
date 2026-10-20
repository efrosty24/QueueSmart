# QueueSmart

Monorepo with a React frontend and a Python FastAPI backend. It runs locally with Node and Python; Docker is optional.

## Structure

```
QueueSmart/
├── frontend/            # React + TypeScript (Vite)
├── backend/             # Python FastAPI
├── Dockerfile           # optional: frontend image (built with nginx)
└── docker-compose.yml   # optional: frontend + backend together
```

### Backend layout

```
backend/
├── app/
│   ├── main.py          # FastAPI app, routers, CORS
│   ├── errors.py        # 422 validation error format
│   └── auth/            # Authentication module
│       ├── router.py        # /api/auth endpoints
│       ├── schemas.py       # request/response models
│       ├── validation.py    # regex rules: email (username) + password
│       ├── passwords.py     # bcrypt hashing
│       ├── roles.py         # patient vs admin
│       ├── sessions.py      # 7-day session tokens
│       ├── store.py         # in-memory accounts (no database yet)
│       └── dependencies.py  # get_current_user, require_admin
└── tests/               # pytest unit tests
```

### Frontend layout

```
frontend/src/
├── theme/           # design tokens, panel styles, light/dark/system logic
├── components/      # shared UI (AppShell sidebar, ConfirmDialog, PageHeader, TextField, ...)
├── lib/             # API client (api.ts) and small helpers (date/time formatting)
├── mocks/           # mock data: services, live queue timeline, visit history
└── features/
    ├── auth/        # login, registration, validation, session, route guards (calls the backend)
    ├── dashboard/   # overview: current queue + recent visits
    ├── join/        # service selection, wait estimates, join/leave controls
    ├── queue/       # Queue status screen
    └── history/     # History screen
```

Styling follows the shared theme. **Read [frontend/THEMING.md](frontend/THEMING.md) before writing UI.**

## Features so far

- **Login** (`/login`) and **Registration** (`/register`), backed by the FastAPI auth module. Email is the username.
- Validation on both sides: email format (an allowlist that also blocks SQL-injection input), password rules (8–64 characters with an uppercase letter and a special character), and matching confirmation on sign-up. The server re-checks everything.
- **Sessions:** signing in returns a token that lasts **7 days**. It's kept in the browser and re-checked with the server on every page load. **Sign out** revokes it on the server.
- **Roles:** an account is an **admin** when the name part of its email (before the @) contains "admin"; everyone else is a patient. The role always comes from the server, and admin pages require it.
- **Route guards:** signed-out users who open a signed-in page are sent to `/login`. Signed-in users who open `/login` or `/register` go to `/admin` or `/dashboard` depending on their role.
- **Sidebar layout** for signed-in pages, with Dashboard, Queue status and History. Below 900px it becomes a slide-in menu. **Sign out** is a pill that turns red on hover and asks for confirmation in a popup.
- **Dashboard** (`/dashboard`): current queue, available campus clinic services and estimated waits, recent in-app notifications, and the three most recent visits.
- **Join queue** (`/join-queue`): select an open service, preview its wait, and join. Students can have one active queue at a time. Leaving requires confirmation and records a Left queue visit in History.
- **Queue status** (`/queue`): current position, estimated wait, people ahead, and status (Waiting → Almost ready → Served), with a feed of status updates.
- **History** (`/history`): past queues with date, service, wait and outcome (Served, Left queue, No-show), summary totals, and an outcome filter.
- Light, dark and system themes: red brand color on solid neutral backgrounds.

### Mock data

Sign-in runs on the backend (see [Backend API](#backend-api)). Everything else still runs on mock data in `frontend/src/mocks/`:

| File | What it fakes |
|---|---|
| `services.ts` | Clinic services (Sick Visit, Flu Shot, Prescription Refill, Lab Work) and their expected minutes per patient |
| `serviceQueues.ts` | Service descriptions, queue availability and sample numbers of students waiting |
| `activeQueue.ts` | The patient's current queue entry and a scripted timeline of what happens to it |
| `history.ts` | 12 past visits across the fall semester |

- **Queue state:** new students start without an active queue. Joining a service creates a mock ticket, and the queue advances every 15 seconds until Served. State survives navigation and reloads in the same tab and is separated by student email. Completed and left visits remain in that tab's History when another queue is joined.
- **Live queue demo:** **Start queue demo** on an empty Queue status page runs the original Sick Visit timeline, including a staff-priority delay. **Restart demo** restarts the current timeline. Notifications use the same queue events as Queue status. This is accelerated sample data, not a real clinic queue.
- **Wait estimate:** people ahead × the service's expected minutes per patient.

## Setup

### Prerequisites

- [Node.js](https://nodejs.org/) 26 (current release)
- npm 12.2 or newer. Node 26 ships with npm 11, so upgrade it once:

  ```bash
  npm install -g npm@latest
  ```

  Check with `npm -v`.
- [Python](https://www.python.org/) 3.13 (for the backend)
- [Docker](https://www.docker.com/) is **optional**. You only need it to try the containers (see [Optional: run with Docker](#optional-run-with-docker)).

### Clone

```bash
git clone https://github.com/efrosty24/QueueSmart.git
cd QueueSmart
```

### Run locally

This is the normal way to run QueueSmart while developing: no Docker needed. Use two terminals.

Start the backend first (terminal 1):

```bash
cd backend
python3.13 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/uvicorn app.main:app --reload --port 8000
```

On Windows, use `.venv\Scripts\pip` and `.venv\Scripts\uvicorn` instead of `.venv/bin/...` (and `python` or `py -3.13` instead of `python3.13`).

API docs are at http://localhost:8000/docs.

Then the frontend (terminal 2):

```bash
cd frontend
npm install
npm run dev      # http://localhost:5173
```

Open http://localhost:5173. The Vite dev server forwards `/api` to the backend on port 8000, so the two connect automatically. Other frontend scripts: `npm run build`, `npm run preview`, `npm run lint`.

### Backend tests and coverage

```bash
cd backend
.venv/bin/pytest
```

This runs the unit tests and prints a coverage report. The run fails if coverage drops below 80%. For an HTML report, add `--cov-report=html` and open `htmlcov/index.html`.

### Optional: run with Docker

Skip this if you don't use Docker; nothing else depends on it. It's handy for a one-command demo, since it needs no local Node or Python. From the repo root:

```bash
docker compose up --build
```

Then open http://localhost:8080 (not 5173). nginx serves the frontend and forwards `/api` to the backend container (config in `frontend/nginx.conf`). The frontend image builds on Node 26 with npm 12.2.0. To use a different npm version, pass `--build-arg NPM_VERSION=<version>`.

## Backend API

No database yet (that's Assignment 4): accounts and sessions live in memory and reset when the server restarts.

### Demo accounts

Created on every start (test values only):

| Email | Password | Role |
|---|---|---|
| `admin@university.edu` | `Queue$mart1` | admin |
| `student@university.edu` | `Queue$mart1` | patient |

### Auth endpoints

| Method | Path | Body | Returns |
|---|---|---|---|
| `POST` | `/api/auth/register` | `{email, password}` | `201` `{token, expires_at, user}`, signed in right away |
| `POST` | `/api/auth/login` | `{email, password}` | `200` `{token, expires_at, user}` |
| `GET` | `/api/auth/me` | — | `200` `{id, email, role}` for the current token |
| `POST` | `/api/auth/logout` | — | `204`, token revoked |
| `GET` | `/api/health` | — | `200` `{status: "ok"}` |

Send the token as `Authorization: Bearer <token>`. `user` is `{id, email, role}`, with `role` either `patient` or `admin`.

### Rules

- **Email (username):** trimmed and lowercased, at most 254 characters (64 before the @). Checked against an **allowlist** regex of characters found in real addresses, so quotes, `;`, `=`, spaces, `/` and `*` can never get through. `--` (SQL comment) and `..` are rejected too. This protects the username field from SQL injection once a database is added.
- **Password at sign-up:** 8–64 characters (and at most 72 bytes, bcrypt's limit), with at least one uppercase letter and one special character (anything that isn't a letter, digit or space).
- **Password at login:** required, same length cap.
- **Types and extra fields:** values must be strings (no numbers or lists). Unknown fields are rejected, so a client can't send `"role": "admin"`.
- **Passwords** are hashed with **bcrypt** (cost 12) and never stored or returned in plain text.
- **Roles:** admin if the email's name part contains "admin" (`clinic.admin@university.edu` yes, `jane@admin.edu` no). Admin-only endpoints use the `require_admin` dependency: `401` without a session, `403` for patients.
- **Sessions** last 7 days. The server keeps only a SHA-256 hash of each token.

### Errors

| Status | When | Body |
|---|---|---|
| `401` | Wrong email/password, or a missing, expired or revoked token | `{detail}` (one generic login message, so it doesn't reveal which emails exist) |
| `403` | A patient calls an admin-only endpoint | `{detail}` |
| `409` | Registering an email that already has an account | `{detail}` |
| `422` | Missing fields, wrong types, values too long, or a rule failed | `{detail, errors: {field: message}}` |
