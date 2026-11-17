from __future__ import annotations

import uuid
from collections.abc import Iterator

from fastapi import Depends, HTTPException, Request
from sqlmodel import Session

from app import repo
from app.models import Profile
from app.service import AppState


def get_state(request: Request) -> AppState:
    return request.app.state.core


def get_session(request: Request) -> Iterator[Session]:
    with Session(request.app.state.core.engine) as session:
        yield session


def profile_or_404(profile_id: uuid.UUID, session: Session = Depends(get_session)) -> Profile:
    profile = repo.get_profile(session, profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ")
    return profile
