import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from backend.config import get_settings
from backend.routes import (
    appointments,
    auth,
    clinical,
    documents,
    pages,
    patients,
    reminders,
    staff,
    audit,
    workflows,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("agentcare.main")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Idempotent: creates any tables that don't exist yet and seeds synthetic
    # demo data only if none is present (backend/seed/seed_data.py skips
    # itself once departments exist). Safe to run on every startup, including
    # against an already-migrated local/production database — it's what
    # keeps ephemeral deployments (e.g. Vercel's /tmp-backed SQLite, wiped on
    # every cold start) bootable without a persistent database attached.
    # Skipped under APP_ENV=test: pytest's TestClient triggers this same
    # lifespan, but tests bind their own isolated in-memory engine and must
    # never touch the real module-level SessionLocal (see tests/conftest.py).
    if settings.app_env != "test":
        from backend.seed.seed_data import seed

        try:
            seed()
        except Exception:
            logger.exception("Startup schema/seed check failed")
    yield


app = FastAPI(
    title="AgentCare",
    description="Agentic AI for patient administration and care coordination",
    lifespan=lifespan,
)

app.mount(
    "/static",
    StaticFiles(directory=str(settings.base_dir / "src" / "frontend" / "static")),
    name="static",
)

app.include_router(auth.router, prefix="/api")
app.include_router(patients.router, prefix="/api")
app.include_router(clinical.router, prefix="/api")
app.include_router(appointments.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(workflows.router, prefix="/api")
app.include_router(reminders.router, prefix="/api")
app.include_router(staff.router, prefix="/api")
app.include_router(audit.router, prefix="/api")
app.include_router(pages.router)


@app.get("/healthz")
def healthz():
    return {"status": "ok"}
