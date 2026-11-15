from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse


app = FastAPI(title="Vigo API")
static_dir = Path(__file__).parent / "static"


@app.get("/", include_in_schema=False)
def home() -> FileResponse:
    return FileResponse(static_dir / "index.html")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
