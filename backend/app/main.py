from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .auth.router import router as auth_router
from .errors import register_error_handlers
from .queues import router as queues_router
from .services import router as services_router
from .notifications import router as notifications_router
from .history import router as history_router

app = FastAPI(title="QueueSmart API", version="0.1.0")

# The Vite dev server proxies /api, so CORS only matters when calling the API
# from another origin during development (for example, a separate tool).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
register_error_handlers(app)
app.include_router(auth_router)
app.include_router(services_router)
app.include_router(queues_router)
app.include_router(notifications_router)
app.include_router(history_router)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
