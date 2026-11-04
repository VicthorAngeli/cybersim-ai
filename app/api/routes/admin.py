from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles
from app.core.config import get_settings
from app.core.security import hash_password
from app.db.models import AuditLog, BusinessCalendar, Company, User
from app.db.session import get_db
from app.schemas.api import HolidayCreate, UserCreate

router = APIRouter(prefix="/admin", tags=["Administração"])


@router.get("/settings")
def settings_view(user: User = Depends(require_roles("admin"))) -> dict:
    del user
    settings = get_settings()
    return {
        "llm_provider": settings.llm_provider,
        "openai_model": settings.openai_model,
        "openai_api_key_configured": bool(settings.openai_api_key),
        "timeout_seconds": settings.openai_timeout,
        "max_retries": settings.openai_max_retries,
        "max_tokens_per_call": settings.openai_max_tokens,
    }


@router.get("/users")
def list_users(db: Session = Depends(get_db), user: User = Depends(require_roles("admin"))) -> list[dict]:
    records = db.scalars(select(User).order_by(User.email))
    return [
        {"id": row.id, "email": row.email, "role": row.role, "company_id": row.company_id, "active": row.active}
        for row in records
    ]


@router.post("/users", status_code=201)
def create_user(
    data: UserCreate,
    db: Session = Depends(get_db),
    current: User = Depends(require_roles("admin")),
) -> dict:
    email = data.email.strip().casefold()
    if db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(status_code=409, detail="Já existe usuário com este e-mail.")
    if data.company_id and not db.get(Company, data.company_id):
        raise HTTPException(status_code=404, detail="Empresa não encontrada.")
    record = User(
        email=email, password_hash=hash_password(data.password),
        role=data.role, company_id=data.company_id,
    )
    db.add(record)
    db.flush()
    db.add(AuditLog(
        company_id=record.company_id, user_id=current.id, action="user.created",
        resource_type="user", resource_id=record.id, details={"role": record.role},
    ))
    db.commit()
    return {"id": record.id, "email": record.email, "role": record.role, "company_id": record.company_id}


@router.get("/calendar")
def list_holidays(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "facilitator")),
) -> list[dict]:
    query = select(BusinessCalendar).order_by(BusinessCalendar.holiday_date)
    if user.role != "admin":
        query = query.where(BusinessCalendar.company_id == user.company_id)
    return [
        {"id": row.id, "holiday_date": row.holiday_date.isoformat(), "description": row.description}
        for row in db.scalars(query)
    ]


@router.post("/calendar", status_code=201)
def add_holiday(
    data: HolidayCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "facilitator")),
) -> dict:
    company_id = data.company_id if user.role == "admin" else user.company_id
    if not company_id:
        raise HTTPException(status_code=422, detail="Defina a empresa para cadastrar feriados.")
    if user.role != "admin" and data.company_id and data.company_id != user.company_id:
        raise HTTPException(status_code=404, detail="Empresa não encontrada.")
    if not db.get(Company, company_id):
        raise HTTPException(status_code=404, detail="Empresa não encontrada.")
    if db.scalar(select(BusinessCalendar.id).where(
        BusinessCalendar.company_id == company_id,
        BusinessCalendar.holiday_date == data.holiday_date,
    )):
        raise HTTPException(status_code=409, detail="Já existe feriado cadastrado nesta data.")
    holiday = BusinessCalendar(
        company_id=company_id,
        holiday_date=data.holiday_date,
        description=data.description,
    )
    db.add(holiday)
    db.commit()
    db.refresh(holiday)
    return {"id": holiday.id, "holiday_date": holiday.holiday_date.isoformat(), "description": holiday.description}


@router.get("/audit")
def audit_history(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "facilitator")),
    limit: int = 100,
) -> list[dict]:
    if not 1 <= limit <= 500:
        raise HTTPException(status_code=422, detail="limit deve estar entre 1 e 500.")
    query = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
    if user.role != "admin":
        query = query.where(AuditLog.company_id == user.company_id)
    return [
        {"id": row.id, "action": row.action, "resource_type": row.resource_type,
         "resource_id": row.resource_id, "created_at": row.created_at.isoformat()}
        for row in db.scalars(query)
    ]
