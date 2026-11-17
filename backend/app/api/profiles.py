from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from sqlmodel import Session

from app import repo
from app.ai.recommend import Article, recommend
from app.api.deps import get_session, get_state, profile_or_404
from app.core.fees import apply_fees
from app.core.ledger import build_ledger
from app.core.portfolio import compute_portfolio
from app.core.risk import score
from app.core.validate import validate
from app.models import Profile
from app.schemas import (
    Level,
    Metrics,
    PortfolioView,
    ProfileCreate,
    ProfileOut,
    TradeRow,
    ValidationResult,
)
from app.service import AppState, analyze, to_priced

router = APIRouter(prefix="/profiles", tags=["profiles"])
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
NO_TRADES = "Chưa có dữ liệu giao dịch"


@router.post("", response_model=ProfileOut)
def create_profile(body: ProfileCreate, state: AppState = Depends(get_state),
                   session: Session = Depends(get_session)) -> ProfileOut:
    try:
        risk = score(body.answers, state.cfg)
    except ValueError as e:
        raise HTTPException(status_code=422,
                            detail="Cần đúng 5 câu trả lời, mỗi câu trả lời là số nguyên từ 1 đến 4") from e
    profile = repo.create_profile(session, body.answers, risk.score, risk.tier.value, risk.level.value)
    return ProfileOut(id=str(profile.id), tier=risk.tier, level=risk.level)


@router.post("/{profile_id}/trades", response_model=ValidationResult,
             responses={422: {"model": ValidationResult}})
def upload_trades(file: UploadFile, profile: Profile = Depends(profile_or_404),
                  state: AppState = Depends(get_state), session: Session = Depends(get_session)):
    data = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Tệp quá lớn (tối đa 5 MB)")
    result = validate(data, state.prices)
    if result.errors:
        return JSONResponse(status_code=422, content=result.model_dump(mode="json"))
    priced = apply_fees(result.rows, state.cfg)
    repo.replace_trades(session, profile.id, priced)
    return ValidationResult(rows=priced, errors=[], warnings=result.warnings)


@router.get("/{profile_id}/trades", response_model=list[TradeRow])
def list_trades(profile: Profile = Depends(profile_or_404), session: Session = Depends(get_session)):
    return to_priced(repo.list_trades(session, profile.id))


@router.get("/{profile_id}/metrics", response_model=Metrics)
def get_metrics(profile: Profile = Depends(profile_or_404), state: AppState = Depends(get_state),
                session: Session = Depends(get_session)) -> Metrics:
    trades = to_priced(repo.list_trades(session, profile.id))
    if not trades:
        raise HTTPException(status_code=409, detail=NO_TRADES)
    return analyze(profile, trades, state)


@router.get("/{profile_id}/articles", response_model=list[Article])
def get_articles(profile: Profile = Depends(profile_or_404), state: AppState = Depends(get_state),
                 session: Session = Depends(get_session)) -> list[Article]:
    trades = to_priced(repo.list_trades(session, profile.id))
    flags = analyze(profile, trades, state).flags if trades else []
    return recommend(flags, Level(profile.level), state.articles)


@router.get("/{profile_id}/portfolio", response_model=PortfolioView)
def get_portfolio(profile: Profile = Depends(profile_or_404), state: AppState = Depends(get_state),
                  session: Session = Depends(get_session)) -> PortfolioView:
    trades = to_priced(repo.list_trades(session, profile.id))
    if not trades:
        raise HTTPException(status_code=409, detail=NO_TRADES)
    pf = compute_portfolio(trades, build_ledger(trades, state.prices), state.prices)
    return PortfolioView(first_date=pf.first_date, last_date=pf.last_date, rebased=pf.rebased,
                         weights_symbol=pf.weights_symbol, weights_sector=pf.weights_sector)
