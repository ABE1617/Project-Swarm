import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import FRONTEND_DIST
from app.db import init_db
from app.engine.registry import get_registry
from app.routes import auth_routes, node_routes, run_routes, workflow_routes

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    get_registry()
    yield


app = FastAPI(title="Project Swarm", version="2.0.0", lifespan=lifespan)

# Vite dev server during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_routes.router)
app.include_router(workflow_routes.router)
app.include_router(run_routes.router)
app.include_router(node_routes.router)


if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa(full_path: str):
        if full_path.startswith("api/") or full_path == "api":
            raise HTTPException(status_code=404)
        candidate = FRONTEND_DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")
else:

    @app.get("/", include_in_schema=False)
    async def no_frontend():
        return {
            "app": "Project Swarm v2 API",
            "hint": "Frontend not built yet - run `npm run build` in frontend/, or use the Vite dev server on :5173",
        }
