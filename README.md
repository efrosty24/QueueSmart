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
│   ├── services.py      # service routes, validation, in-memory records
│   ├── wait_time.py     # reusable people-ahead × duration calculation
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
    ├── services/    # shared service API calls and patient service loading
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
- **Service management** (`/admin/services`): admins create, edit and delete services through the backend. The admin dashboard can open or close a service. The patient dashboard and join page load this same list, including new services. Services are kept in memory and reset when the backend restarts.
- **Wait estimates (Module 4):** the backend calculates each service's estimated wait and returns `estimatedWaitMinutes`. Service cards on the dashboard and join page display this response value.
- **Route guards:** signed-out users who open a signed-in page are sent to `/login`. Signed-in users who open `/login` or `/register` go to `/admin` or `/dashboard` depending on their role.
- **Sidebar layout** for signed-in pages, with Dashboard, Queue status and History. Below 900px it becomes a slide-in menu. **Sign out** is a pill that turns red on hover and asks for confirmation in a popup.
- **Dashboard** (`/dashboard`): current queue, available campus clinic services and estimated waits, recent in-app notifications, and the three most recent visits.
- **Join queue** (`/join-queue`): select an open service, preview its wait, and join. Students can have one active queue at a time. Leaving requires confirmation and records a Left queue visit in History.
- **Queue status** (`/queue`): current position, estimated wait, people ahead, and status (Waiting → Almost ready → Served), with a feed of status updates.
- **History** (`/history`): past queues with date, service, wait and outcome (Served, Left queue, No-show), summary totals, and an outcome filter.
- Light, dark and system themes: red brand color on solid neutral backgrounds.

### Mock data

Authentication and service management run on the backend (see [Backend API](#backend-api)). Queue actions, notifications and history are still frontend demos:

| File | What it fakes |
|---|---|
| `services.ts` | Legacy service details for the scripted queue demo and old mock visits; live service lists use the API |
| `activeQueue.ts` | The patient's current queue entry and a scripted timeline of what happens to it |
| `history.ts` | 12 past visits across the fall semester |

- **Queue state:** new students start without an active queue. Joining a service creates a mock ticket, and the queue advances every 15 seconds until Served. State survives navigation and reloads in the same tab and is separated by student email. Completed and left visits remain in that tab's History when another queue is joined.
- **Live queue demo:** **Start queue demo** on an empty Queue status page runs the original Sick Visit timeline, including a staff-priority delay. **Restart demo** restarts the current timeline. Notifications use the same queue events as Queue status. This is accelerated sample data, not a real clinic queue.
- **Wait estimate:** service previews use the backend's `estimatedWaitMinutes`. The active queue's scripted demo still calculates its own changing wait until Module 3 supplies actual backend queue positions.
- **Queue counts:** the service API returns placeholder counts (`queueLength`) until Module 3 implements real queue management. Admin queue actions still use their own frontend demo. Patient service lists reload when the page opens or the tab regains focus.

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

No database yet (that's Assignment 4): accounts, sessions and services live in memory and reset when the server restarts. Run one backend process so requests share that memory.

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

### Service endpoints (Module 2)

All service requests require `Authorization: Bearer <token>`. Patients and admins can list services; all changes require an admin.

| Method | Path | Body | Returns |
|---|---|---|---|
| `GET` | `/api/services` | — | `200` list of services |
| `POST` | `/api/services` | `{name, description, expectedDurationMinutes, priority}` | `201` new service |
| `PUT` | `/api/services/{id}` | All four service fields | `200` updated service |
| `PATCH` | `/api/services/{id}/status` | `{status: "open"}` or `{status: "closed"}` | `200` updated service |
| `DELETE` | `/api/services/{id}` | — | `204`, no body |

Service responses include `id`, `name`, `description`, `expectedDurationMinutes`, `priority`, `status`, the placeholder `queueLength`, and the calculated `estimatedWaitMinutes`. New services start closed with a generated ID and a count of zero. Updating details preserves the ID, availability and count, and recalculates the estimate using the new duration. The estimate is calculated when returning a service, so it stays in sync with the current count and duration. Clients cannot submit their own estimate.

Names and descriptions are required text, trimmed before validation, with limits of 100 and 1,000 characters. Duration must be a whole number from 1 to 480 (strings, decimals and booleans are rejected). Priority must be `low`, `medium` or `high`. Unknown fields are rejected. Invalid input returns `422` with field errors, missing services return `404`, missing/invalid sessions return `401`, and patient changes return `403`.

The service tests cover create/list/update/delete, availability, permissions, validation boundaries, and rejected requests leaving data unchanged. Queue joining, serving, notifications and history backend endpoints belong to later modules.

### Wait-time estimation (Module 4)

`app/wait_time.py` provides `estimate_wait(people_ahead, duration_minutes)`. It returns the number of people ahead multiplied by the expected minutes per patient. Counts must be non-negative whole numbers and durations must be positive whole numbers; invalid values raise `ValueError`.

Service previews pass `queueLength` as the number of people ahead. For example, Sick Visit starts with 4 people waiting at 12 minutes each, so its API estimate is 48 minutes. Empty queues return zero. Closed services still include a numeric estimate, while the UI displays "Unavailable".

Module 3 can reuse the same helper for an individual user by passing `position - 1` and the service duration. A person at position 1 has no one ahead and waits zero estimated minutes. Queue counts are still mocked until Module 3 is implemented; no new queue endpoints or database are included here.

Tests cover normal estimates, zero wait, invalid values, changed queue counts and durations, and preventing clients from overriding the calculated field.

### Authentication rules

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
| `404` | A service ID does not exist | `{detail}` |
| `409` | Registering an email that already has an account | `{detail}` |
| `422` | Missing fields, wrong types, values too long, or a rule failed | `{detail, errors: {field: message}}` |
