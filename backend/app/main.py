from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from backend.app.routes import demo, grow, health, shield

BASE_DIR = Path(__file__).resolve().parents[2]
FRONTEND_DIR = BASE_DIR / "frontend" / "static"

app = FastAPI(
    title="FIDES MVP",
    description="FastAPI scaffold for FIDES Shield and FIDES Grow.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(demo.router)
app.include_router(shield.router)
app.include_router(grow.router)

app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/", include_in_schema=False)
def index() -> RedirectResponse:
    return RedirectResponse(url="/grow", status_code=307)


@app.get("/shield", include_in_schema=False)
def shield_page() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "shield.html")


@app.get("/grow", include_in_schema=False)
def grow_page() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "grow.html")
