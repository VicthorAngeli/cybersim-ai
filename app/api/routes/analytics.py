from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.analytics.powerbi_exporter import export_zip
from app.db.models import AgentRun, ActionItem, CommunicationDraft, Decision, Exercise, Finding, User
from app.db.session import get_db

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/export")
def export_analytics(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    company_id = None if user.role == "admin" else user.company_id
    if user.role != "admin" and not company_id:
        raise HTTPException(status_code=403, detail="Usuário sem empresa autorizada para exportação.")
    payload, result = export_zip(db, company_id=company_id)
    return Response(
        content=payload,
        media_type="application/zip",
        headers={
            "Content-Disposition": 'attachment; filename="cybersim-powerbi-csv.zip"',
            "X-Export-Record-Count": str(result["total_rows"]),
        },
    )


@router.get("/summary")
def analytics_summary(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    def count(model: type, *filters: object) -> int:
        statement = select(func.count(model.id))
        if user.role != "admin":
            statement = statement.where(model.company_id == user.company_id)
        for clause in filters:
            statement = statement.where(clause)
        return int(db.scalar(statement) or 0)

    return {
        "total_exercises": count(Exercise),
        "completed_exercises": count(Exercise, Exercise.status == "concluido"),
        "in_progress_exercises": count(Exercise, Exercise.status == "em_andamento"),
        "decisions": count(Decision),
        "findings": count(Finding),
        "pending_actions": count(ActionItem, ActionItem.status == "pendente"),
        "agent_runs": count(AgentRun),
        "pending_communications": count(CommunicationDraft, CommunicationDraft.approval_status != "aprovado"),
    }


@router.get("/recent")
def recent_exercises(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[dict]:
    query = select(Exercise).order_by(Exercise.created_at.desc()).limit(10)
    if user.role != "admin":
        query = query.where(Exercise.company_id == user.company_id)
    return [
        {"id": row.id, "title": row.title, "status": row.status,
         "created_at": row.created_at.isoformat(), "company_id": row.company_id}
        for row in db.scalars(query)
    ]
