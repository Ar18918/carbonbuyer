"""FastAPI application entrypoint."""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import analytics, auth, buyers, exports, projects, research, saved
from app.config import settings
from app.db.base import Base
from app.db.session import engine

logging.basicConfig(level=logging.INFO)

app = FastAPI(title=settings.app_name, version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    # Ensure schema exists. (Use `alembic upgrade head` in production instead.)
    Base.metadata.create_all(bind=engine)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok", "app": settings.app_name}


p = settings.api_v1_prefix
for r in (auth.router, projects.router, buyers.router, analytics.router,
          research.router, exports.router, saved.router):
    app.include_router(r, prefix=p)
