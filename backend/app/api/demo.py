from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import text
from sqlmodel import Session

from app import repo
from app.api.deps import get_session, get_state
from app.config import Thresholds
from app.core.fees import apply_fees
from app.core.risk import score
from app.core.validate import validate
from app.schemas import DemoItem
from app.service import AppState, read_json

router = APIRouter()

TEMPLATE_CSV = (
    "trade_date,symbol,side,quantity,price,fee,tax\n"
    "2026-03-02,FPT,BUY,100,100000,,\n"
    "2026-03-16,FPT,SELL,100,104000,,\n"
    "2026-03-18,VCB,BUY,200,60000,,\n"
)


@router.get("/demo", response_model=list[DemoItem], tags=["demo"])
def list_demo(state: AppState = Depends(get_state)) -> list[DemoItem]:
    path = state.settings.personas_dir / "personas.json"
    if not path.exists():
        return []
    return [DemoItem.model_validate({k: v for k, v in p.items() if k != "labels"}) for p in read_json(path)]


@router.post("/demo/{persona_id}/load", tags=["demo"])
def load_demo(persona_id: str, state: AppState = Depends(get_state), session: Session = Depends(get_session)):
    d = state.settings.personas_dir
    csv_path = d / f"{persona_id}_s1.csv"
    answers = (read_json(d / "answers.json") if (d / "answers.json").exists() else {}).get(persona_id)
    if answers is None or not csv_path.exists():
        raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ demo")
    result = validate(csv_path.read_bytes(), state.prices)
    if result.errors:
        raise HTTPException(status_code=500, detail="Dữ liệu hồ sơ demo không hợp lệ")
    risk = score(answers, state.cfg)
    profile = repo.create_profile(session, answers, risk.score, risk.tier.value, risk.level.value,
                                  persona_id=persona_id)
    repo.replace_trades(session, profile.id, apply_fees(result.rows, state.cfg))
    return {"id": str(profile.id)}


@router.get("/template.csv", tags=["demo"])
def template_csv() -> Response:
    return Response(TEMPLATE_CSV, media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": 'attachment; filename="template.csv"'})


@router.get("/health", tags=["demo"])
def health(session: Session = Depends(get_session)) -> dict:
    try:
        session.exec(text("select 1"))
        return {"ok": True, "db": True}
    except Exception:
        return {"ok": False, "db": False}


@router.get("/thresholds", response_model=Thresholds, tags=["demo"])
def get_thresholds(state: AppState = Depends(get_state)) -> Thresholds:
    """The thresholds in force, so the UI can show 'value vs threshold' without hard-coding any."""
    return state.cfg
