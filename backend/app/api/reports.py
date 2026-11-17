from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app import repo
from app.ai.prompts import round_floats
from app.ai.report import build_report
from app.api.deps import get_session, get_state, profile_or_404
from app.models import Profile, Report
from app.schemas import Metrics, ReportContent, ReportOut, Violation
from app.service import AppState, analyze, to_priced

router = APIRouter(prefix="/profiles", tags=["reports"])


def to_out(row: Report) -> ReportOut:
    return ReportOut(
        id=str(row.id), created_at=row.created_at.isoformat(), formula_version=row.formula_version,
        model=row.model, attempts=row.attempts, passed=row.passed,
        violations=[Violation.model_validate(v) for v in row.violations], latency_ms=row.latency_ms,
        content=ReportContent.model_validate(row.content), metrics=Metrics.model_validate(row.metrics))


@router.post("/{profile_id}/reports", response_model=ReportOut)
def create_report(profile: Profile = Depends(profile_or_404), state: AppState = Depends(get_state),
                  session: Session = Depends(get_session)) -> ReportOut:
    trades = to_priced(repo.list_trades(session, profile.id))
    if not trades:
        raise HTTPException(status_code=409, detail="Chưa có dữ liệu giao dịch")
    fingerprint = repo.data_hash(trades, state.cfg.formula_version)
    cached = repo.find_report_by_hash(session, profile.id, fingerprint)
    # A report that fell back to the template because the API itself failed (bad key, quota, outage)
    # says nothing about the data, so it must not be served again once the API works.
    if cached is not None and not any(v.get("code") == "llm_error" for v in cached.violations):
        return to_out(cached)
    if state.llm is None:
        raise HTTPException(status_code=503, detail="Chưa cấu hình LLM (đặt LLM_API_KEY) nên chưa tạo được báo cáo AI")
    metrics = analyze(profile, trades, state)
    result = build_report(metrics, state.llm, state.cfg, state.symbols)
    row = repo.save_report(
        session, profile.id, data_hash=fingerprint, formula_version=state.cfg.formula_version,
        model=result.model, attempts=result.attempts, passed=result.passed,
        violations=[v.model_dump(mode="json") for v in result.violations], latency_ms=result.latency_ms,
        metrics=round_floats(metrics.model_dump(mode="json")), content=result.content.model_dump(mode="json"))
    return to_out(row)


@router.get("/{profile_id}/reports/latest", response_model=ReportOut)
def latest_report(profile: Profile = Depends(profile_or_404), session: Session = Depends(get_session)) -> ReportOut:
    row = repo.latest_report(session, profile.id)
    if row is None:
        raise HTTPException(status_code=404, detail="Chưa có báo cáo nào cho hồ sơ này")
    return to_out(row)
