import uuid
from datetime import date

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from app import repo
from app.db import make_engine, normalize_url, run_migrations
from app.models import Profile, Trade
from app.schemas import PricedTrade, Side


@pytest.fixture
def engine(tmp_path):
    eng = make_engine(f"sqlite:///{tmp_path / 'test.db'}")
    run_migrations(f"sqlite:///{tmp_path / 'test.db'}")
    return eng


def trade(n, qty=100, symbol="AAA", side=Side.BUY):
    return PricedTrade(row_no=n, trade_date=date(2026, 1, 5), symbol=symbol, side=side, quantity=qty,
                       price=10_000, fee=30, tax=0)


def test_normalize_url_adds_psycopg_driver():
    assert normalize_url("postgresql://u:p@h/db?sslmode=require").startswith("postgresql+psycopg://")
    assert normalize_url("postgresql+psycopg://u@h/db") == "postgresql+psycopg://u@h/db"
    assert normalize_url("sqlite:///x.db") == "sqlite:///x.db"


def test_migration_on_empty_database_creates_three_tables(engine):
    names = set(inspect(engine).get_table_names())
    assert {"profiles", "trades", "reports"} <= names


def test_db_check_constraints_mirror_pydantic(engine):
    pid = uuid.uuid4()
    with Session(engine) as s:
        s.add(Profile(id=pid, answers=[1] * 5, score=5, tier="conservative", level="beginner"))
        s.commit()
        s.add(Trade(profile_id=pid, row_no=1, trade_date=date(2026, 1, 5), symbol="AAA", side="BUY",
                    quantity=0, price=1, fee=0, tax=0))
        with pytest.raises(IntegrityError):
            s.commit()
        s.rollback()
        s.add(Profile(id=uuid.uuid4(), answers=[1] * 5, score=5, tier="nonsense", level="beginner"))
        with pytest.raises(IntegrityError):
            s.commit()


def test_create_profile_and_get(engine):
    with Session(engine) as s:
        p = repo.create_profile(s, answers=[2, 2, 2, 2, 2], score=10, tier="balanced", level="intermediate")
        assert repo.get_profile(s, p.id).tier == "balanced"
        assert repo.get_profile(s, uuid.uuid4()) is None


def test_replace_trades_replaces_old_rows(engine):
    with Session(engine) as s:
        p = repo.create_profile(s, [2] * 5, 10, "balanced", "intermediate", persona_id=None)
        repo.replace_trades(s, p.id, [trade(1), trade(2)])
        repo.replace_trades(s, p.id, [trade(1, symbol="BBB")])
        rows = repo.list_trades(s, p.id)
        assert [(r.symbol, r.quantity) for r in rows] == [("BBB", 100)]


def test_replace_trades_is_atomic(engine):
    with Session(engine) as s:
        p = repo.create_profile(s, [2] * 5, 10, "balanced", "intermediate")
        repo.replace_trades(s, p.id, [trade(1), trade(2)])
        bad = PricedTrade.model_construct(**{**trade(1).model_dump(), "quantity": 0})  # skips pydantic, hits CHECK
        with pytest.raises(IntegrityError):
            repo.replace_trades(s, p.id, [trade(1, symbol="CCC"), bad])
        assert len(repo.list_trades(s, p.id)) == 2  # old rows survived


def test_deleting_profile_cascades_to_trades(engine):
    with Session(engine) as s:
        p = repo.create_profile(s, [2] * 5, 10, "balanced", "intermediate")
        repo.replace_trades(s, p.id, [trade(1)])
        s.delete(s.get(Profile, p.id))
        s.commit()
        assert s.exec(text("select count(*) from trades")).scalar() == 0


def test_reports_cache_by_data_hash_and_latest(engine):
    with Session(engine) as s:
        p = repo.create_profile(s, [2] * 5, 10, "balanced", "intermediate")
        r1 = repo.save_report(s, p.id, data_hash="h1", formula_version="0.1", model="m", attempts=1,
                              passed=True, violations=[], latency_ms=5, metrics={"a": 1}, content={"b": 2})
        assert repo.find_report_by_hash(s, p.id, "h1").id == r1.id
        assert repo.find_report_by_hash(s, p.id, "other") is None
        r2 = repo.save_report(s, p.id, data_hash="h2", formula_version="0.1", model="m", attempts=2,
                              passed=False, violations=["advice"], latency_ms=9, metrics={}, content={})
        assert repo.latest_report(s, p.id).id == r2.id
        assert repo.latest_report(s, uuid.uuid4()) is None


def test_data_hash_depends_on_trades_and_formula_version():
    a = repo.data_hash([trade(1), trade(2)], "0.1")
    assert a == repo.data_hash([trade(2), trade(1)], "0.1")  # order-insensitive
    assert a != repo.data_hash([trade(1), trade(2, qty=200)], "0.1")
    assert a != repo.data_hash([trade(1), trade(2)], "0.2")
