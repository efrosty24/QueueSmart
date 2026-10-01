# QueueSmart

Monorepo with a React frontend and a Python FastAPI backend, containerized with Docker.

## Structure

```
QueueSmart/
├── frontend/   # React + TypeScript (Vite)
└── backend/    # FastAPI (coming soon)
```

### Frontend layout

```
frontend/src/
├── theme/           # design tokens, panel styles, light/dark/system logic
├── components/      # shared UI (AppShell sidebar, ConfirmDialog, PageHeader, TextField, ...)
├── lib/             # small helpers (date/time formatting)
├── mocks/           # mock data: services, live queue timeline, visit history
└── features/
    ├── auth/        # login, registration, validation, mock session, route guards
    ├── dashboard/   # overview: current queue + recent visits
    ├── queue/       # Queue status screen
    └── history/     # History screen
```

Styling follows the shared theme. **Read [frontend/THEMING.md](frontend/THEMING.md) before writing UI.**

## Features so far

- **Login** (`/login`) and **Registration** (`/register`). Email is the username.
- Client-side validation: required fields, email format, password rules (8+ characters with a letter and a number), and matching confirmation on sign-up.
- **Mock sign-in:** a valid login or registration signs the user in and redirects to **`/dashboard`**. The session is kept in the browser, so it survives a reload. **Sign out** clears it.
- **Route guards:** signed-out users who open a signed-in page are sent to `/login`. Signed-in users who open `/login` or `/register` are sent to `/dashboard`.
- **Sidebar layout** for signed-in pages, with Dashboard, Queue status and History. Below 900px it becomes a slide-in menu. **Sign out** is a pill that turns red on hover and asks for confirmation in a popup.
- **Dashboard** (`/dashboard`): a snapshot of the current queue and the three most recent visits.
- **Queue status** (`/queue`): current position, estimated wait, people ahead, and status (Waiting → Almost ready → Served), with a feed of status updates.
- **History** (`/history`): past queues with date, service, wait and outcome (Served, Left queue, No-show), summary totals, and an outcome filter.
- Light, dark and system themes: red brand color on solid neutral backgrounds.

### Mock data

There is no backend yet, so everything runs on mock data in `frontend/src/mocks/`:

| File | What it fakes |
|---|---|
| `services.ts` | Clinic services (Sick Visit, Flu Shot, Prescription Refill, Lab Work) and their expected minutes per patient |
| `activeQueue.ts` | The patient's current queue entry and a scripted timeline of what happens to it |
| `history.ts` | 12 past visits across the fall semester |

- **Auth:** any valid email and password is accepted, and every account is a patient (`features/auth/authApi.ts`).
- **Live queue demo:** the queue moves forward one step every 15 seconds, including an urgent case that pushes the patient back once, until they're served. Progress keeps going while you switch pages and starts over in a new tab. **Restart demo** on the Queue status page starts it again. Once it reaches Served, today's visit appears at the top of History.
- **Wait estimate:** people ahead × the service's expected minutes per patient.

## Setup

### Prerequisites

- [Node.js](https://nodejs.org/) 26 (current release)
- npm 12.2 or newer. Node 26 ships with npm 11, so upgrade it once:

  ```bash
  npm install -g npm@latest
  ```

  Check with `npm -v`.
- [Docker](https://www.docker.com/) (for running the container)

### Clone

```bash
git clone https://github.com/efrosty24/QueueSmart.git
cd QueueSmart
```

### Run locally

```bash
cd frontend
npm install
npm run dev      # http://localhost:5173
```

Other scripts: `npm run build`, `npm run preview`, `npm run lint`.

### Run with Docker

From the repo root:

```bash
docker build -t queuesmart .
docker run --rm -p 8080:80 queuesmart
```

Then open http://localhost:8080. The image builds the frontend on Node 26 with npm 12.2.0 and serves it with nginx (config in `frontend/nginx.conf`). To use a different npm version, pass `--build-arg NPM_VERSION=<version>` to `docker build`.

### Backend

Not yet added.

## Extending: adding the admin view

The admin dashboard UI (services, live queues, reports) is **not built yet**. These steps add the admin *route and sign-in path* using only client-side logic, so the real admin pages can be dropped in later. The groundwork is already there: every session has a `role` of `'patient'` or `'admin'` (`features/auth/session.ts`).

> Client-side roles are for UI only. Anyone can edit `localStorage` and make themselves an "admin". The FastAPI backend must check roles on every request once it exists.

**1. Give some mock accounts the admin role.** In `features/auth/authApi.ts`, decide the role from a mock list instead of always returning `'patient'`:

```ts
// Mock staff accounts until the backend decides roles.
const MOCK_ADMIN_EMAILS = ['admin@university.edu']

function toSessionUser(email: string): SessionUser {
  const normalized = email.trim().toLowerCase()
  return { email: normalized, role: MOCK_ADMIN_EMAILS.includes(normalized) ? 'admin' : 'patient' }
}
```

Use `toSessionUser(credentials.email)` as the return value of `login()`. Keep `register()` creating patients only, since staff accounts are set up by the clinic, not through public sign-up.

**2. Add a role guard.** In `features/auth/RouteGuards.tsx`, next to `RequireAuth`:

```tsx
export function RequireRole({ role }: { role: Role }) {
  const { user } = useAuth()
  if (user?.role !== role) return <Navigate to="/dashboard" replace />
  return <Outlet />
}
```

**3. Send each role to its own home page.** Add a helper and use it wherever the code currently navigates to `'/dashboard'` (`LoginPage`, `RegisterPage`, `RedirectIfSignedIn`, and the catch-all route in `App.tsx`):

```ts
export const homePathFor = (user: SessionUser) => (user.role === 'admin' ? '/admin' : '/dashboard')
```

**4. Create a placeholder admin page.** Add `features/admin/AdminDashboardPage.tsx`, built like `DashboardPage`: a `<PageHeader>` and a `.glass` card saying "Admin dashboard (coming soon)". Nest its route inside the `<AppShell />` route so it gets the sidebar, and add an Admin link to `navItems` in `AppShell.tsx` (shown only when `user.role === 'admin'`). Follow [THEMING.md](frontend/THEMING.md) for styles.

**5. Register the route** in `App.tsx`, nested so it needs both a session and the admin role:

```tsx
<Route element={<RequireAuth />}>
  <Route path="/dashboard" element={<DashboardPage />} />
  <Route element={<RequireRole role="admin" />}>
    <Route path="/admin" element={<AdminDashboardPage />} />
  </Route>
</Route>
```

**6. Validate admin forms on the client the same way as auth.** When the service form is built, put its rules in `features/admin/validation.ts`, following `features/auth/validation.ts`. Each rule is a small function that returns an error message or `undefined`. Based on the A1 design, a service needs:
- **Name:** required, 100 characters or fewer
- **Description:** optional, 500 characters or fewer
- **Expected duration:** a whole number of minutes, 1 to 240
- **Priority:** one of a fixed set, for example `low`, `medium`, `high`

The form hook `features/auth/useAuthForm.ts` isn't specific to auth. Move it to `src/components/useForm.ts` (or similar) and reuse it for admin forms.

**7. Test it by hand.**
- Sign in as `admin@university.edu`. You should land on `/admin`.
- Sign in as any other email. You should land on `/dashboard`, and opening `/admin` should send you back to `/dashboard`.
- Sign out. Opening `/admin` should send you to `/login`.
