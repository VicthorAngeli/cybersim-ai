from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_roles
from app.db.models import AuditLog, Company, User
from app.db.session import get_db
from app.schemas.api import CompanyCreate, CompanyRead

router = APIRouter(prefix="/companies", tags=["Empresas"])


@router.get("", response_model=list[CompanyRead])
def list_companies(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Company]:
    query = select(Company).order_by(Company.name)
    if user.role != "admin":
        if not user.company_id:
            return []
        query = query.where(Company.id == user.company_id)
    return list(db.scalars(query))


@router.post("", response_model=CompanyRead, status_code=201)
def create_company(
    data: CompanyCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin")),
) -> Company:
    company = Company(**data.model_dump())
    db.add(company)
    db.flush()
    db.add(AuditLog(
        company_id=company.id, user_id=user.id, action="company.created",
        resource_type="company", resource_id=company.id, details={},
    ))
    db.commit()
    db.refresh(company)
    return company


@router.get("/{company_id}", response_model=CompanyRead)
def get_company(
    company_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Company:
    company = db.get(Company, company_id)
    if not company or (user.role != "admin" and user.company_id != company_id):
        raise HTTPException(status_code=404, detail="Empresa não encontrada.")
    return company
