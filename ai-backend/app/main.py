from fastapi import FastAPI

from app.api.incidents import router as incident_router

from app.models.db import init_db

app = FastAPI(
    title="AI-Assisted Incident Analysis API",
    version="0.1.0",
)

@app.on_event("startup")
def startup():
    init_db()

@app.get("/")
def root():
    return {
        "service": "AI-Assisted Incident Analysis API",
        "status": "running"
    }


@app.get("/health")
def health():
    return {"status": "healthy"}

app.include_router(incident_router)
