from __future__ import annotations

from fastapi import FastAPI

from .routers import master, document

app = FastAPI(title="AMDlingo Agent Service")
app.include_router(master.router)
app.include_router(document.router)


@app.get("/healthz")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
