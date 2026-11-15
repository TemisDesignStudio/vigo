from datetime import date
import json
import os
from pathlib import Path
from secrets import token_urlsafe
import re
import time
from typing import Literal
from urllib.error import HTTPError, URLError
from urllib.request import Request as UrlRequest, urlopen

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from database import connect, now, password_matches
from knowledge import VIGO_ADMIN_ASSISTANT_INSTRUCTIONS, VIGO_ASSISTANT_INSTRUCTIONS


app = FastAPI(title="Vigo API")
frontend_dir = Path(__file__).parents[1] / "frontend" / "out"
sessions: set[str] = set()
CAMPAIGN_STATUSES = {"new", "reviewing", "approved", "active", "completed", "rejected"}
COLLABORATION_STATUSES = {"new", "reviewing", "approved", "rejected"}
OPENROUTER_MODEL = "openrouter/free"


class LoginInput(BaseModel):
    username: str
    password: str


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=1000)

    @field_validator("content")
    @classmethod
    def valid_content(cls, value: str) -> str:
        return checked_text(value)


class ChatInput(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=8)

    @model_validator(mode="after")
    def last_message_is_user(self) -> "ChatInput":
        if self.messages[-1].role != "user":
            raise ValueError("پیام آخر باید از کاربر باشد.")
        return self


class AssistantOperation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal["create", "update", "status"]
    resource: Literal["campaign", "collaboration_request"]
    record_id: int | None = Field(default=None, gt=0)
    data: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def valid_operation_shape(self) -> "AssistantOperation":
        if self.action == "create" and self.record_id is not None:
            raise ValueError("create نباید شناسه داشته باشد.")
        if self.action != "create" and self.record_id is None:
            raise ValueError("عملیات به شناسه نیاز دارد.")
        if not self.data:
            raise ValueError("عملیات به داده نیاز دارد.")
        return self


class AssistantOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str = Field(min_length=1, max_length=1000)
    operation: AssistantOperation | None = None

    @field_validator("message")
    @classmethod
    def valid_message(cls, value: str) -> str:
        return checked_text(value)


class AdminAssistantInput(ChatInput):
    pass


class OpenRouterError(Exception):
    def __init__(self, status_code: int | None = None):
        self.status_code = status_code


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


def request_openrouter(messages: list[ChatMessage], api_key: str) -> str:
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [{"role": "system", "content": VIGO_ASSISTANT_INSTRUCTIONS}, *[message.model_dump() for message in messages]],
        "max_tokens": 350,
        "temperature": 0.35,
    }
    return request_openrouter_payload(payload, api_key)


def request_openrouter_payload(payload: dict, api_key: str) -> str:
    request = UrlRequest(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json", "X-Title": "Vigo Website Assistant"},
        method="POST",
    )
    for attempt in range(2):
        try:
            with urlopen(request, timeout=30) as response:
                data = json.loads(response.read())
            break
        except HTTPError as error:
            if attempt == 0 and error.code >= 500:
                time.sleep(0.5)
                continue
            raise OpenRouterError(error.code) from error
        except (URLError, TimeoutError, json.JSONDecodeError):
            if attempt == 0:
                time.sleep(0.5)
                continue
            raise OpenRouterError() from None

    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    if isinstance(content, list):
        content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
    if not isinstance(content, str) or not content.strip():
        raise OpenRouterError()
    return content.strip()


def admin_context() -> dict[str, list[dict]]:
    with connect() as connection:
        campaigns = connection.execute(
            "SELECT id, brand_name, requester_name, objective, status FROM campaigns ORDER BY id DESC LIMIT 20"
        ).fetchall()
        collaboration_requests = connection.execute(
            "SELECT id, name, social_network, activity_field, status FROM collaboration_requests ORDER BY id DESC LIMIT 20"
        ).fetchall()
    return {"campaigns": [dict(row) for row in campaigns], "collaboration_requests": [dict(row) for row in collaboration_requests]}


def normalize_reference(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("ي", "ی").replace("ك", "ک").strip()).casefold()


def reference_id(value: str) -> int:
    return int(value.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")))


def resolve_admin_references(instruction: str, context: dict[str, list[dict]]) -> dict:
    normalized_instruction = normalize_reference(instruction)
    resource = "collaboration_request" if "همکاری" in normalized_instruction else "campaign"
    records = context["collaboration_requests"] if resource == "collaboration_request" else context["campaigns"]
    record_ids = {item["id"] for item in records}
    resolved = []
    for raw_id in re.findall(r"(?:شماره|شناسه|id)\s*([0-9۰-۹]+)", normalized_instruction, flags=re.IGNORECASE):
        record_id = reference_id(raw_id)
        if record_id in record_ids:
            resolved.append({"resource": resource, "id": record_id, "reason": "explicit_id"})

    name_field = "name" if resource == "collaboration_request" else "brand_name"
    name_matches = [item for item in records if normalize_reference(item[name_field]) in normalized_instruction]
    if len(name_matches) > 1:
        matches = ", ".join(f"{item[name_field]} (شناسه {item['id']})" for item in name_matches)
        label = "نام درخواست همکاری" if resource == "collaboration_request" else "نام کمپین"
        return {"resolved": resolved, "ambiguous": f"{label} مبهم است: {matches}. لطفاً شناسه را مشخص کنید."}
    if len(name_matches) == 1:
        match = name_matches[0]
        resolved.append({"resource": resource, "id": match["id"], "reason": "unique_name", "name": match[name_field]})
    return {"resolved": resolved, "ambiguous": None}


def direct_status_operation(instruction: str, resolution: dict) -> AssistantOperation | None:
    normalized_instruction = normalize_reference(instruction)
    if "وضعیت" not in normalized_instruction or len(resolution["resolved"]) != 1:
        return None
    reference = resolution["resolved"][0]
    statuses = CAMPAIGN_STATUSES if reference["resource"] == "campaign" else COLLABORATION_STATUSES
    requested = [value for value in statuses if re.search(rf"(?<![a-z]){re.escape(value)}(?![a-z])", normalized_instruction)]
    if len(requested) != 1:
        return None
    return AssistantOperation(action="status", resource=reference["resource"], record_id=reference["id"], data={"status": requested[0]})


def request_admin_assistant(messages: list[ChatMessage], context: dict, api_key: str) -> str:
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": VIGO_ADMIN_ASSISTANT_INSTRUCTIONS},
            {"role": "system", "content": f"Current Vigo data: {json.dumps(context, ensure_ascii=False)}"},
            *[message.model_dump() for message in messages],
        ],
        "max_tokens": 500,
        "temperature": 0.2,
    }
    return request_openrouter_payload(payload, api_key)


def operation_error() -> HTTPException:
    return HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="خروجی دستیار معتبر نیست و هیچ تغییری اعمال نشد.")


def parse_assistant_output(raw_output: str) -> AssistantOutput:
    cleaned = raw_output.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", cleaned, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        cleaned = fenced.group(1)
    try:
        parsed, _ = json.JSONDecoder().raw_decode(cleaned[cleaned.index("{") :])
    except (ValueError, json.JSONDecodeError) as error:
        raise operation_error() from error
    if not isinstance(parsed, dict):
        raise operation_error()

    operation = parsed.get("operation")
    if isinstance(operation, dict):
        action = operation.get("action", operation.get("type"))
        resource = operation.get("resource", operation.get("record_type"))
        aliases = {
            "change_status": "status",
            "update_status": "status",
            "campaigns": "campaign",
            "collaboration": "collaboration_request",
            "collaboration_requests": "collaboration_request",
        }
        action = aliases.get(action, action)
        resource = aliases.get(resource, resource)
        data = operation.get("data", operation.get("fields", {}))
        if not data and "status" in operation:
            data = {"status": operation["status"]}
        parsed["operation"] = {
            "action": action,
            "resource": resource,
            "record_id": operation.get("record_id", operation.get("id", operation.get("campaign_id", operation.get("collaboration_request_id")))),
            "data": data,
        }
    try:
        return AssistantOutput.model_validate(parsed)
    except ValidationError as error:
        raise operation_error() from error


def apply_assistant_operation(operation: AssistantOperation) -> dict:
    table = "campaigns" if operation.resource == "campaign" else "collaboration_requests"
    input_model = CampaignInput if operation.resource == "campaign" else CollaborationInput
    allowed_fields = set(input_model.model_fields)

    if operation.action == "create":
        if set(operation.data) - allowed_fields:
            raise operation_error()
        try:
            record = insert_record(table, input_model.model_validate(operation.data).model_dump(mode="json"), created_by_user_id=1)
        except ValidationError as error:
            raise operation_error() from error
    elif operation.action == "update":
        if set(operation.data) - (allowed_fields - {"status"}):
            raise operation_error()
        existing = get_record(table, operation.record_id)
        merged = {field: operation.data.get(field, existing[field]) for field in allowed_fields}
        try:
            validated = input_model.model_validate(merged).model_dump(mode="json")
        except ValidationError as error:
            raise operation_error() from error
        record = update_record(table, operation.record_id, {field: validated[field] for field in operation.data})
    else:
        if set(operation.data) != {"status"}:
            raise operation_error()
        valid_statuses = CAMPAIGN_STATUSES if operation.resource == "campaign" else COLLABORATION_STATUSES
        if operation.data["status"] not in valid_statuses:
            raise operation_error()
        record = update_record(table, operation.record_id, {"status": operation.data["status"]})

    return {"action": operation.action, "resource": operation.resource, "record": record}


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/chat")
def chat(payload: ChatInput) -> dict[str, str]:
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    if not api_key or re.search(r"your|replace|placeholder", api_key, re.IGNORECASE):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="کلید OpenRouter در فایل .env پیکربندی نشده است.")
    try:
        return {"message": request_openrouter(payload.messages, api_key)}
    except OpenRouterError as error:
        if error.status_code == status.HTTP_401_UNAUTHORIZED:
            message = "اعتبار دستیار در سرور تأیید نشد."
        elif error.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
            message = "مدل رایگان فعلاً به سقف ظرفیت رسیده است. چند دقیقه دیگر دوباره تلاش کنید."
        elif error.status_code in {status.HTTP_404_NOT_FOUND, status.HTTP_503_SERVICE_UNAVAILABLE}:
            message = "مدل انتخاب‌شده فعلاً در دسترس نیست."
        elif error.status_code is None:
            message = "اتصال به سرویس دستیار برقرار نشد. لطفاً دوباره تلاش کنید."
        else:
            message = "پاسخ‌گویی دستیار با مشکل روبه‌رو شد. لطفاً دوباره تلاش کنید."
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE if error.status_code is None else error.status_code, detail=message) from None


@app.post("/api/admin/assistant", dependencies=[Depends(require_admin)])
def admin_assistant(payload: AdminAssistantInput) -> dict:
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    if not api_key or re.search(r"your|replace|placeholder", api_key, re.IGNORECASE):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="کلید OpenRouter در فایل .env پیکربندی نشده است.")
    context = admin_context()
    resolution = resolve_admin_references(payload.messages[-1].content, context)
    if resolution["ambiguous"]:
        return {"message": resolution["ambiguous"], "change": None}
    context["reference_resolution"] = resolution["resolved"]
    direct_operation = direct_status_operation(payload.messages[-1].content, resolution)
    if direct_operation:
        change = apply_assistant_operation(direct_operation)
        return {"message": "وضعیت رکورد با موفقیت تغییر کرد.", "change": change}
    try:
        raw_output = request_admin_assistant(payload.messages, context, api_key)
    except OpenRouterError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="پاسخ‌گویی دستیار مدیریتی با مشکل روبه‌رو شد. لطفاً دوباره تلاش کنید.") from error
    output = parse_assistant_output(raw_output)

    change = apply_assistant_operation(output.operation) if output.operation else None
    return {"message": output.message, "change": change}


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
