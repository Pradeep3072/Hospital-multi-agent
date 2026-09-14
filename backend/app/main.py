import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config import settings
from backend.app.database.session import init_db
from backend.app.database.seed import seed_database
from backend.app.api.chat import router as chat_router
from backend.app.api.patients import router as patients_router
from backend.app.api.doctors import router as doctors_router
from backend.app.api.appointments import router as appointments_router
from backend.app.api.hospital import router as hospital_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Full-Stack Hospital Multi-Agent AI System powered by Google ADK architecture, FastAPI, and PostgreSQL.",
    version="1.0.0"
)

# Enable CORS for Streamlit frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(chat_router, prefix="/api/v1")
app.include_router(patients_router, prefix="/api/v1")
app.include_router(doctors_router, prefix="/api/v1")
app.include_router(appointments_router, prefix="/api/v1")
app.include_router(hospital_router, prefix="/api/v1")


@app.on_event("startup")
def startup_event():
    init_db()
    seed_database()


@app.get("/")
def root():
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "docs": "/docs",
        "api_v1": "/api/v1"
    }


@app.get("/api/v1/health")
def healthcheck():
    return {
        "status": "healthy",
        "system": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "database": "connected",
        "adk_orchestration": "active",
        "rag_retriever": "ready"
    }


if __name__ == "__main__":
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
