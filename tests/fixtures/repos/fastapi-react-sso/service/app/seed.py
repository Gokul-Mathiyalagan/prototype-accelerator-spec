"""Load synthetic seed data on first start."""

import json
from datetime import date
from pathlib import Path

from sqlalchemy import select

from app.db import Base, SessionLocal, engine
from app.models import Team, TeamMember

SEED = Path(__file__).resolve().parent.parent / "data" / "seed_members.json"


def seed() -> None:
    Base.metadata.create_all(engine)
    with SessionLocal() as session:
        if session.scalar(select(Team).limit(1)) is not None:
            return
        for team_data in json.loads(SEED.read_text()):
            team = Team(name=team_data["team"])
            for m in team_data["members"]:
                team.members.append(
                    TeamMember(
                        name=m["name"],
                        role=m["role"],
                        email=m["email"],
                        start_date=date.fromisoformat(m["start_date"]),
                    )
                )
            session.add(team)
        session.commit()
