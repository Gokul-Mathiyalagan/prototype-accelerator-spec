"""Team endpoints, versioned under /api/v1."""

import csv
import io

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import require_role
from app.db import get_session
from app.errors import ApiError
from app.llm import gateway
from app.models import Team, TeamMember

router = APIRouter(prefix="/api/v1")


def _team(session: Session, team_id: int) -> Team:
    team = session.get(Team, team_id)
    if team is None:
        raise ApiError(404, "not_found", f"No team {team_id}.")
    return team


@router.get("/teams/{team_id}/members")
def list_members(
    team_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: str = require_role("viewer"),
    session: Session = Depends(get_session),
) -> dict:
    """Paginated members: {"items": [...], "page", "page_size", "total"}."""
    _team(session, team_id)
    query = select(TeamMember).where(TeamMember.team_id == team_id).order_by(TeamMember.name)
    total = session.scalar(select(func.count()).select_from(query.subquery()))
    rows = session.scalars(query.offset((page - 1) * page_size).limit(page_size)).all()
    items = [
        {"name": m.name, "role": m.role, "start_date": m.start_date.isoformat()} for m in rows
    ]
    return {"items": items, "page": page, "page_size": page_size, "total": total}


@router.get("/teams/{team_id}/members.csv")
def export_members(
    team_id: int,
    user: str = require_role("analyst"),
    session: Session = Depends(get_session),
) -> StreamingResponse:
    """CSV export; analysts and admins only."""
    team = _team(session, team_id)
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["name", "role", "start_date"])
    for m in team.members:
        writer.writerow([m.name, m.role, m.start_date.isoformat()])
    return StreamingResponse(iter([out.getvalue()]), media_type="text/csv")


@router.get("/teams/{team_id}/summary")
def summarize_team(
    team_id: int,
    user: str = require_role("viewer"),
    session: Session = Depends(get_session),
) -> dict:
    team = _team(session, team_id)
    members = "; ".join(f"{m.role} since {m.start_date.year}" for m in team.members)
    return {"summary": gateway.complete("team_summary", team_name=team.name, members=members)}
