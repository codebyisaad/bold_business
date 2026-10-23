from fastapi import FastAPI

from app.routers import candidates

app = FastAPI(title="TechForce")
app.include_router(candidates.router)
