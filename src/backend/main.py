import logging

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
settings = get_settings()

app = FastAPI(title="AgentCare", description="Agentic AI for patient administration and care coordination")

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
