from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import candidates, recruiters

app = FastAPI(title="TechForce")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["X-Recruiter-Id"],
)
app.include_router(candidates.router)
app.include_router(recruiters.router)
