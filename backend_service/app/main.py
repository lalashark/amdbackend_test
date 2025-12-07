from __future__ import annotations

from fastapi import FastAPI

from .routers import analysis, session

app = FastAPI(title="AMDlingo Backend")
app.include_router(analysis.router)
app.include_router(session.router)


@app.get("/healthz")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
