"""OpenClaw server — FastAPI entry point."""

import os
import yaml
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.storage.database import Database
from server.core.ai_router import AIRouter
from server.core.chat_engine import ChatEngine
from server.api import routes_chat, routes_sessions, routes_health
from server.api.middleware import set_auth_token

# ── Load config ──
_config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
if not os.path.exists(_config_path):
    _config_path = os.path.join(os.path.dirname(__file__), "config.example.yaml")

with open(_config_path, "r", encoding="utf-8") as f:
    CONFIG = yaml.safe_load(f) or {}

# ── Init components ──
_db_path = os.path.join(os.path.dirname(__file__), CONFIG.get("database", {}).get("path", "data/openclaw.db"))
db = Database(_db_path)
ai_router = AIRouter(CONFIG)
chat_engine = ChatEngine(db, ai_router)

# ── Wire dependencies ──
set_auth_token(CONFIG.get("server", {}).get("auth_token", ""))
routes_chat.set_engine(chat_engine)
routes_sessions.set_db(db)

# ── Create app ──
app = FastAPI(title="OpenClaw", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_health.router, prefix="/api/v1")
app.include_router(routes_chat.router, prefix="/api/v1")
app.include_router(routes_sessions.router, prefix="/api/v1")


@app.on_event("shutdown")
def shutdown():
    db.close()
