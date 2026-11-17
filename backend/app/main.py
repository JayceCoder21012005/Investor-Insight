"""FastAPI app. PriceStore, thresholds and articles load once at startup; invalid config stops the app."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import Engine

from app.ai.llm import LLMClient, build_llm
from app.ai.recommend import load_articles
from app.api import demo, profiles, reports
from app.config import Settings, load_thresholds
from app.core.prices import PriceStore
from app.db import make_engine
from app.service import AppState


def create_app(settings: Settings | None = None, llm: LLMClient | None = None,
               engine: Engine | None = None) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        llm_client = llm if llm is not None else build_llm(settings)
        app.state.core = AppState(
            settings=settings,
            cfg=load_thresholds(settings.thresholds_path),
            prices=PriceStore(settings.prices_dir),
            articles=load_articles(settings.articles_dir),
            engine=engine or make_engine(settings.database_url),
            llm=llm_client,
        )
        yield

    app = FastAPI(title="Investor Insight API", lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=[settings.cors_origin], allow_methods=["*"],
                       allow_headers=["*"])

    @app.exception_handler(RequestValidationError)
    async def validation_handler(_: Request, exc: RequestValidationError):
        fields = ", ".join(".".join(str(p) for p in e["loc"][1:]) or str(e["loc"][0]) for e in exc.errors())
        return JSONResponse(status_code=422, content={"detail": f"Dữ liệu gửi lên không hợp lệ ({fields})"})

    for router in (profiles.router, reports.router, demo.router):
        app.include_router(router, prefix="/api")
    return app


app = create_app()
