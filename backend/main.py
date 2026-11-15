from pathlib import Path
from secrets import token_urlsafe

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel


app = FastAPI(title="Vigo API")
frontend_dir = Path(__file__).parents[1] / "frontend" / "out"
sessions: set[str] = set()


class LoginInput(BaseModel):
    username: str
    password: str


def authenticated(request: Request) -> bool:
    return request.cookies.get("vigo_session") in sessions


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/auth/login")
def login(credentials: LoginInput, response: Response) -> dict[str, str]:
    if credentials.username != "user" or credentials.password != "password":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="نام کاربری یا رمز عبور نادرست است.")

    session = token_urlsafe(32)
    sessions.add(session)
    response.set_cookie("vigo_session", session, httponly=True, samesite="lax", secure=False)
    return {"username": "user"}


@app.post("/api/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response) -> None:
    session = request.cookies.get("vigo_session")
    if session:
        sessions.discard(session)
    response.delete_cookie("vigo_session", httponly=True, samesite="lax")


@app.get("/api/auth/me")
def current_user(request: Request) -> dict[str, str]:
    if not authenticated(request):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="نیاز به ورود دارید.")
    return {"username": "user"}


@app.get("/admin", include_in_schema=False)
@app.get("/admin/{path:path}", include_in_schema=False)
def admin(request: Request, path: str = ""):
    if not authenticated(request):
        return RedirectResponse("/login", status_code=status.HTTP_303_SEE_OTHER)
    target = frontend_dir / "admin" / (path or "index.html")
    if not target.is_file() or frontend_dir not in target.resolve().parents:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return FileResponse(target)


app.mount(
    "/",
    StaticFiles(directory=frontend_dir, html=True, check_dir=False),
    name="frontend",
)
