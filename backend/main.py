from datetime import date
from pathlib import Path
from secrets import token_urlsafe
import re

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator, model_validator

from database import connect, now, password_matches


app = FastAPI(title="Vigo API")
frontend_dir = Path(__file__).parents[1] / "frontend" / "out"
sessions: set[str] = set()
CAMPAIGN_STATUSES = {"new", "reviewing", "approved", "active", "completed", "rejected"}
COLLABORATION_STATUSES = {"new", "reviewing", "approved", "rejected"}


class LoginInput(BaseModel):
    username: str
    password: str


def checked_text(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("مقدار ضروری است.")
    return value


def checked_contact(value: str) -> str:
    value = checked_text(value)
    if "@" in value and re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
        return value
    if 7 <= len(re.sub(r"\D", "", value)) <= 15:
        return value
    raise ValueError("شماره تماس یا ایمیل نامعتبر است.")


class CampaignInput(BaseModel):
    brand_name: str = Field(min_length=1)
    requester_name: str = Field(min_length=1)
    contact: str = Field(min_length=1)
    budget: int = Field(ge=0)
    objective: str = Field(min_length=1)
    start_date: date | None = None
    end_date: date | None = None
    description: str | None = None
    status: str = "new"

    @field_validator("brand_name", "requester_name", "objective")
    @classmethod
    def required_text(cls, value: str) -> str:
        return checked_text(value)

    @field_validator("contact")
    @classmethod
    def valid_contact(cls, value: str) -> str:
        return checked_contact(value)

    @field_validator("status")
    @classmethod
    def valid_status(cls, value: str) -> str:
        if value not in CAMPAIGN_STATUSES:
            raise ValueError("وضعیت کمپین نامعتبر است.")
        return value

    @model_validator(mode="after")
    def valid_dates(self) -> "CampaignInput":
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("بازه زمانی نامعتبر است.")
        return self


class CampaignUpdate(BaseModel):
    brand_name: str | None = Field(default=None, min_length=1)
    requester_name: str | None = Field(default=None, min_length=1)
    contact: str | None = Field(default=None, min_length=1)
    budget: int | None = Field(default=None, ge=0)
    objective: str | None = Field(default=None, min_length=1)
    start_date: date | None = None
    end_date: date | None = None
    description: str | None = None


class CollaborationInput(BaseModel):
    name: str = Field(min_length=1)
    contact: str = Field(min_length=1)
    social_network: str = Field(min_length=1)
    profile_url: str = Field(min_length=1)
    activity_field: str = Field(min_length=1)
    description: str | None = None
    status: str = "new"

    @field_validator("name", "social_network", "activity_field")
    @classmethod
    def required_text(cls, value: str) -> str:
        return checked_text(value)

    @field_validator("contact")
    @classmethod
    def valid_contact(cls, value: str) -> str:
        return checked_contact(value)

    @field_validator("profile_url")
    @classmethod
    def valid_profile_url(cls, value: str) -> str:
        value = checked_text(value)
        if not re.fullmatch(r"https?://[^\s]+", value):
            raise ValueError("نشانی پروفایل نامعتبر است.")
        return value

    @field_validator("status")
    @classmethod
    def valid_status(cls, value: str) -> str:
        if value not in COLLABORATION_STATUSES:
            raise ValueError("وضعیت درخواست همکاری نامعتبر است.")
        return value


class CollaborationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    contact: str | None = Field(default=None, min_length=1)
    social_network: str | None = Field(default=None, min_length=1)
    profile_url: str | None = Field(default=None, min_length=1)
    activity_field: str | None = Field(default=None, min_length=1)
    description: str | None = None


class StatusInput(BaseModel):
    status: str = Field(min_length=1)


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, __: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content={"detail": "اطلاعات ارسالی نامعتبر است."})


def authenticated(request: Request) -> bool:
    return request.cookies.get("vigo_session") in sessions


def require_admin(request: Request) -> None:
    if not authenticated(request):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="نیاز به ورود مدیر دارید.")


def get_record(table: str, record_id: int) -> dict:
    with connect() as connection:
        row = connection.execute(f"SELECT * FROM {table} WHERE id = ?", (record_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="رکورد موردنظر یافت نشد.")
    return dict(row)


def insert_record(table: str, data: dict, created_by_user_id: int | None = None) -> dict:
    data["created_by_user_id"] = created_by_user_id
    data["created_at"] = now()
    data["updated_at"] = data["created_at"]
    columns = list(data)
    placeholders = ", ".join("?" for _ in columns)
    with connect() as connection:
        cursor = connection.execute(f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})", list(data.values()))
        record_id = cursor.lastrowid
    return get_record(table, record_id)


def update_record(table: str, record_id: int, data: dict) -> dict:
    if not data:
        return get_record(table, record_id)
    data["updated_at"] = now()
    assignments = ", ".join(f"{column} = ?" for column in data)
    with connect() as connection:
        cursor = connection.execute(f"UPDATE {table} SET {assignments} WHERE id = ?", [*data.values(), record_id])
        if cursor.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="رکورد موردنظر یافت نشد.")
    return get_record(table, record_id)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/auth/login")
def login(credentials: LoginInput, response: Response) -> dict[str, str]:
    with connect() as connection:
        user = connection.execute("SELECT * FROM users WHERE username = ?", (credentials.username,)).fetchone()
    if user is None or not password_matches(credentials.password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="نام کاربری یا رمز عبور نادرست است.")
    session = token_urlsafe(32)
    sessions.add(session)
    response.set_cookie("vigo_session", session, httponly=True, samesite="lax", secure=False)
    return {"username": user["username"]}


@app.post("/api/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response) -> None:
    session = request.cookies.get("vigo_session")
    if session:
        sessions.discard(session)
    response.delete_cookie("vigo_session", httponly=True, samesite="lax")


@app.get("/api/auth/me")
def current_user(request: Request) -> dict[str, str]:
    require_admin(request)
    return {"username": "user"}


@app.post("/api/campaigns", status_code=status.HTTP_201_CREATED)
def create_public_campaign(payload: CampaignInput) -> dict:
    return insert_record("campaigns", payload.model_dump(mode="json"))


@app.post("/api/collaboration-requests", status_code=status.HTTP_201_CREATED)
def create_public_collaboration_request(payload: CollaborationInput) -> dict:
    return insert_record("collaboration_requests", payload.model_dump(mode="json"))


@app.get("/api/admin/campaigns", dependencies=[Depends(require_admin)])
def list_campaigns() -> list[dict]:
    with connect() as connection:
        rows = connection.execute("SELECT * FROM campaigns ORDER BY id DESC").fetchall()
    return [dict(row) for row in rows]


@app.post("/api/admin/campaigns", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])
def create_campaign(payload: CampaignInput) -> dict:
    return insert_record("campaigns", payload.model_dump(mode="json"), created_by_user_id=1)


@app.get("/api/admin/campaigns/{record_id}", dependencies=[Depends(require_admin)])
def get_campaign(record_id: int) -> dict:
    return get_record("campaigns", record_id)


@app.patch("/api/admin/campaigns/{record_id}", dependencies=[Depends(require_admin)])
def update_campaign(record_id: int, payload: CampaignUpdate) -> dict:
    return update_record("campaigns", record_id, payload.model_dump(exclude_unset=True, mode="json"))


@app.patch("/api/admin/campaigns/{record_id}/status", dependencies=[Depends(require_admin)])
def update_campaign_status(record_id: int, payload: StatusInput) -> dict:
    if payload.status not in CAMPAIGN_STATUSES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="وضعیت کمپین نامعتبر است.")
    return update_record("campaigns", record_id, {"status": payload.status})


@app.get("/api/admin/collaboration-requests", dependencies=[Depends(require_admin)])
def list_collaboration_requests() -> list[dict]:
    with connect() as connection:
        rows = connection.execute("SELECT * FROM collaboration_requests ORDER BY id DESC").fetchall()
    return [dict(row) for row in rows]


@app.post("/api/admin/collaboration-requests", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])
def create_collaboration_request(payload: CollaborationInput) -> dict:
    return insert_record("collaboration_requests", payload.model_dump(mode="json"), created_by_user_id=1)


@app.get("/api/admin/collaboration-requests/{record_id}", dependencies=[Depends(require_admin)])
def get_collaboration_request(record_id: int) -> dict:
    return get_record("collaboration_requests", record_id)


@app.patch("/api/admin/collaboration-requests/{record_id}", dependencies=[Depends(require_admin)])
def update_collaboration_request(record_id: int, payload: CollaborationUpdate) -> dict:
    return update_record("collaboration_requests", record_id, payload.model_dump(exclude_unset=True, mode="json"))


@app.patch("/api/admin/collaboration-requests/{record_id}/status", dependencies=[Depends(require_admin)])
def update_collaboration_status(record_id: int, payload: StatusInput) -> dict:
    if payload.status not in COLLABORATION_STATUSES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="وضعیت درخواست همکاری نامعتبر است.")
    return update_record("collaboration_requests", record_id, {"status": payload.status})


@app.get("/admin", include_in_schema=False)
@app.get("/admin/{path:path}", include_in_schema=False)
def admin(request: Request, path: str = ""):
    if not authenticated(request):
        return RedirectResponse("/login", status_code=status.HTTP_303_SEE_OTHER)
    target = frontend_dir / "admin" / (path or "index.html")
    if not target.is_file() or frontend_dir not in target.resolve().parents:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return FileResponse(target)


app.mount("/", StaticFiles(directory=frontend_dir, html=True, check_dir=False), name="frontend")
