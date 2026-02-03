# path: boat-ride-api/app/main.py

from fastapi import FastAPI
from app.api.routes.routes import router as routes_router

app = FastAPI(title="boat-ride-api")

app.include_router(routes_router)
