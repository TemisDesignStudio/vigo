from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles


app = FastAPI(title="Vigo API")
frontend_dir = Path(__file__).parents[1] / "frontend" / "out"


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.mount(
    "/",
    StaticFiles(directory=frontend_dir, html=True, check_dir=False),
    name="frontend",
)
