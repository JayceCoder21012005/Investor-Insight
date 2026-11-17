"""DEV / E2E ONLY. The real API on a throwaway SQLite database, with a stand-in LLM.

    uv run python scripts/e2e_server.py [--port 8000]

The stand-in answers with the deterministic template text, so the full UI flow (including the AI
report tab) can be exercised without an API key. Its model name says so; never use it for evaluation.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import uvicorn

from app.ai.llm import build_llm
from app.ai.templates import template_content
from app.config import Settings
from app.db import make_engine, run_migrations
from app.main import create_app
from app.schemas import Metrics


class StandInLLM:
    model = "stand-in-llm (e2e, khong phai AI that)"

    def generate_json(self, system: str, user: str, schema: dict) -> dict:
        payload = json.loads(user[user.index("{"):])
        payload["formula_version"] = "e2e"
        return template_content(Metrics.model_validate(payload)).model_dump(mode="json")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--real-llm", action="store_true", help="use the provider configured in .env instead of the stand-in")
    args = ap.parse_args()
    db = Path(tempfile.mkdtemp(prefix="investor_insight_e2e_")) / "e2e.db"
    url = f"sqlite:///{db.as_posix()}"
    run_migrations(url)
    settings = Settings(database_url=url) if args.real_llm else Settings(database_url=url, gemini_api_key="", llm_api_key="")
    llm = build_llm(settings) if args.real_llm else StandInLLM()
    if llm is None:
        raise SystemExit("--real-llm needs GEMINI_API_KEY or LLM_API_KEY in backend/.env")
    print(f"LLM: {llm.model}", flush=True)
    app = create_app(settings=settings, llm=llm, engine=make_engine(url))
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
