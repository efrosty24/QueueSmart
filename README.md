# QueueSmart

Monorepo with a React frontend and a Python FastAPI backend, containerized with Docker.

## Structure

```
QueueSmart/
├── frontend/   # React + TypeScript (Vite)
└── backend/    # FastAPI (coming soon)
```

## Setup

### Prerequisites

- [Node.js](https://nodejs.org/) 20+ (for local development)
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

Then open http://localhost:8080. The image builds the frontend and serves it with nginx.

### Backend

Not yet added.
