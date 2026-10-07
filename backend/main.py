"""FastAPI application and local static-file hosting for FaceGuard."""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.config import FRONTEND_DIR
from backend.database import initialize_database
from backend.routes.areas import router as areas_router
from backend.routes.personnel import router as personnel_router
from backend.routes.recognition import router as access_router
from backend.routes.logs import router as logs_router


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Prepare the local SQLite database when the API starts."""
    initialize_database()
    yield


app = FastAPI(title="FaceGuard", version="0.1.0", lifespan=lifespan)

# Serve frontend assets while keeping the health API under its own path.
app.mount("/css", StaticFiles(directory=FRONTEND_DIR / "css"), name="css")
app.mount("/js", StaticFiles(directory=FRONTEND_DIR / "js"), name="js")
app.include_router(personnel_router)
app.include_router(areas_router)
app.include_router(access_router)
app.include_router(logs_router)


@app.get("/api/health")
def health_check() -> dict[str, str]:
    """Report that the API process is responding."""
    return {"status": "ok", "message": "FaceGuard backend is running."}


@app.get("/", include_in_schema=False)
def home() -> FileResponse:
    """Serve the minimal frontend page from the project root URL."""
    return FileResponse(FRONTEND_DIR / "index.html")


# Make the sibling HTML pages reachable at /personnel.html, /areas.html, etc.
# Keep this catch-all mount last so it cannot shadow the API routes above.
app.mount("/", StaticFiles(directory=FRONTEND_DIR), name="frontend-pages")


