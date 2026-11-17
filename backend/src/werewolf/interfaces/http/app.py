from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from ...bootstrap import build_container
from ..ws.handlers import websocket_endpoint
from .routes import router


def create_app() -> FastAPI:
    app = FastAPI(title="AI 狼人杀 · 幕后智囊团", version="0.1.0")
    app.state.container = build_container()

    extra_origins = [
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "").split(",")
        if origin.strip()
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:4173",
            "http://127.0.0.1:4173",
            *extra_origins,
        ],
        allow_origin_regex=os.getenv(
            "CORS_ORIGIN_REGEX",
            r"https?://(localhost|127\.0\.0\.1|192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}|100\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7])\.\d{1,3}\.\d{1,3})(?::\d+)?",
        ),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)
    app.add_api_websocket_route("/ws/rooms/{code}", websocket_endpoint)

    dist = Path(__file__).resolve().parents[4].parent / "frontend" / "dist"
    if dist.exists():
        app.mount("/", StaticFiles(directory=str(dist), html=True), name="ui")
    return app


app = create_app()
