import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.ai.llm import FakeLLM
from app.ai.templates import template_content
from app.config import Settings
from app.db import make_engine, run_migrations
from app.main import create_app
from app.schemas import Metrics
from scripts.generate_personas import generate_all, load_specs

ROOT = Path(__file__).resolve().parent.parent
GOOD_ANSWERS = [2, 2, 3, 3, 2]


class EchoLLM:
    """Answers with the deterministic template text for the metrics it is shown (always passes guardrails)."""

    model = "echo-llm"

    def __init__(self):
        self.calls = 0

    def generate_json(self, system, user, schema):
        self.calls += 1
        payload = json.loads(user[user.index("{"):])
        payload["formula_version"] = "x"
        return template_content(Metrics.model_validate(payload)).model_dump(mode="json")


@pytest.fixture(scope="module")
def personas_dir(tmp_path_factory, synthetic_store):
    d = tmp_path_factory.mktemp("personas")
    generate_all(synthetic_store, load_specs(ROOT / "scripts" / "persona_specs.yaml"), seeds=1, out_dir=d)
    return d


@pytest.fixture
def make_client(tmp_path, synthetic_dir, personas_dir):
    clients = []

    def factory(llm="default", cors="http://localhost:3000"):
        url = f"sqlite:///{tmp_path / 'api.db'}"
        run_migrations(url)
        settings = Settings(prices_dir=synthetic_dir, personas_dir=personas_dir, articles_dir=ROOT / "content" / "articles",
                            cors_origin=cors, database_url=url, llm_api_key="")
        app = create_app(settings=settings, llm=EchoLLM() if llm == "default" else llm, engine=make_engine(url))
        c = TestClient(app)
        c.__enter__()
        clients.append(c)
        return c

    yield factory
    for c in clients:
        c.__exit__(None, None, None)


@pytest.fixture
def client(make_client):
    return make_client()


def new_profile(client, answers=GOOD_ANSWERS):
    r = client.post("/api/profiles", json={"answers": answers})
    assert r.status_code == 200, r.text
    return r.json()["id"]


def upload(client, pid, csv_text):
    return client.post(f"/api/profiles/{pid}/trades", files={"file": ("t.csv", csv_text.encode("utf-8"), "text/csv")})


def first_trading_days(synthetic_store, n=3):
    return [str(d) for d in synthetic_store.trading_days[10:10 + n]]


# ---------------------------------------------------------------- health, template
def test_health_reports_db_ok(client):
    assert client.get("/api/health").json() == {"ok": True, "db": True}


def test_template_csv_has_the_required_header(client):
    r = client.get("/api/template.csv")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    assert r.text.splitlines()[0] == "trade_date,symbol,side,quantity,price,fee,tax"


# ---------------------------------------------------------------- profiles
def test_create_profile_returns_tier_and_level(client):
    r = client.post("/api/profiles", json={"answers": [1, 1, 1, 1, 1]})
    body = r.json()
    assert r.status_code == 200 and body["tier"] == "conservative" and body["level"] == "beginner" and body["id"]


@pytest.mark.parametrize("answers", [[1, 1, 1, 1], [1, 1, 1, 1, 9], []])
def test_invalid_answers_give_vietnamese_422(client, answers):
    r = client.post("/api/profiles", json={"answers": answers})
    assert r.status_code == 422 and isinstance(r.json()["detail"], str) and "câu trả lời" in r.json()["detail"]


def test_malformed_body_gives_string_detail(client):
    r = client.post("/api/profiles", json={"nope": 1})
    assert r.status_code == 422 and isinstance(r.json()["detail"], str)


# ---------------------------------------------------------------- upload
def test_upload_valid_csv_stores_trades_with_fees_filled(client, synthetic_store):
    pid = new_profile(client)
    a, b = first_trading_days(synthetic_store, 2)
    price = int(synthetic_store.bar("FPT", synthetic_store.trading_days[10]).close // 10 * 10)
    r = upload(client, pid, f"trade_date,symbol,side,quantity,price,fee,tax\n{a},FPT,BUY,100,{price},,\n{b},FPT,SELL,100,{price},,\n")
    assert r.status_code == 200 and r.json()["errors"] == []
    rows = client.get(f"/api/profiles/{pid}/trades").json()
    assert len(rows) == 2 and rows[0]["fee"] > 0 and rows[0]["tax"] == 0 and rows[1]["tax"] > 0


def test_upload_with_oversell_is_422_and_trades_unchanged(client, synthetic_store):
    pid = new_profile(client)
    a, b = first_trading_days(synthetic_store, 2)
    price = int(synthetic_store.bar("FPT", synthetic_store.trading_days[10]).close // 10 * 10)
    assert upload(client, pid, f"trade_date,symbol,side,quantity,price\n{a},FPT,BUY,100,{price}\n").status_code == 200
    bad = upload(client, pid, f"trade_date,symbol,side,quantity,price\n{a},FPT,BUY,100,{price}\n{b},FPT,SELL,500,{price}\n")
    assert bad.status_code == 422
    body = bad.json()
    assert body["rows"] == [] and body["errors"][0]["row"] == 2 and "Dòng 2" in body["errors"][0]["message"]
    assert len(client.get(f"/api/profiles/{pid}/trades").json()) == 1


def test_upload_replaces_previous_trades(client, synthetic_store):
    pid = new_profile(client)
    a, b = first_trading_days(synthetic_store, 2)
    price = int(synthetic_store.bar("FPT", synthetic_store.trading_days[10]).close // 10 * 10)
    upload(client, pid, f"trade_date,symbol,side,quantity,price\n{a},FPT,BUY,100,{price}\n{b},FPT,BUY,200,{price}\n")
    upload(client, pid, f"trade_date,symbol,side,quantity,price\n{a},FPT,BUY,300,{price}\n")
    rows = client.get(f"/api/profiles/{pid}/trades").json()
    assert [r["quantity"] for r in rows] == [300]


def test_upload_warnings_are_returned_on_success(client, synthetic_store):
    pid = new_profile(client)
    a = first_trading_days(synthetic_store, 1)[0]
    price = int(synthetic_store.bar("FPT", synthetic_store.trading_days[10]).close // 10 * 10)
    r = upload(client, pid, f"trade_date,symbol,side,quantity,price\n{a},FPT,BUY,150,{price}\n")
    assert r.status_code == 200 and r.json()["warnings"][0]["field"] == "quantity"


def test_upload_to_unknown_profile_is_404(client):
    r = upload(client, "00000000-0000-0000-0000-000000000000", "trade_date,symbol,side,quantity,price\n")
    assert r.status_code == 404 and "hồ sơ" in r.json()["detail"].lower()


def test_upload_too_large_is_413(client):
    pid = new_profile(client)
    r = client.post(f"/api/profiles/{pid}/trades", files={"file": ("big.csv", b"x" * (5 * 1024 * 1024 + 1))})
    assert r.status_code == 413


def test_upload_without_required_column_is_422_with_file_error(client):
    pid = new_profile(client)
    r = upload(client, pid, "trade_date,symbol\n2026-01-05,FPT\n")
    assert r.status_code == 422 and r.json()["errors"][0]["row"] == 0


# ---------------------------------------------------------------- metrics
def test_metrics_without_trades_is_409(client):
    pid = new_profile(client)
    r = client.get(f"/api/profiles/{pid}/metrics")
    assert r.status_code == 409 and r.json()["detail"] == "Chưa có dữ liệu giao dịch"


def load_demo(client, persona):
    r = client.post(f"/api/demo/{persona}/load")
    assert r.status_code == 200, r.text
    return r.json()["id"]


def test_demo_list_has_all_eleven_personas(client):
    demos = client.get("/api/demo").json()
    assert len(demos) == 11 and set(demos[0]) == {"persona_id", "title", "tier", "description"}


def test_p03_demo_metrics_contain_a_disposition_flag(client):
    pid = load_demo(client, "P03")
    m = client.get(f"/api/profiles/{pid}/metrics").json()
    assert "disposition" in [f["id"] for f in m["flags"]] and m["investor_type"]
    assert m["profile"]["tier"] == "balanced"


def test_unknown_demo_persona_is_404(client):
    assert client.post("/api/demo/P99/load").status_code == 404


# ---------------------------------------------------------------- reports
def test_report_requires_trades(client):
    pid = new_profile(client)
    assert client.post(f"/api/profiles/{pid}/reports").status_code == 409


def test_two_report_posts_without_data_change_return_the_same_report(client):
    pid = load_demo(client, "P03")
    a = client.post(f"/api/profiles/{pid}/reports")
    b = client.post(f"/api/profiles/{pid}/reports")
    assert a.status_code == 200 and a.json()["id"] == b.json()["id"]
    assert a.json()["passed"] is True and a.json()["model"] == "echo-llm"
    assert a.json()["content"]["limitations"]


def test_cached_report_does_not_call_the_llm_again(make_client):
    llm = EchoLLM()
    client = make_client(llm=llm)
    pid = load_demo(client, "P03")
    client.post(f"/api/profiles/{pid}/reports")
    client.post(f"/api/profiles/{pid}/reports")
    assert llm.calls == 1


class FlakyLLM(EchoLLM):
    """Fails like a dead API key / exhausted quota until `up` is set."""

    def __init__(self):
        super().__init__()
        self.up = False

    def generate_json(self, system, user, schema):
        if not self.up:
            raise RuntimeError("API key not valid")
        return super().generate_json(system, user, schema)


def test_report_built_while_the_api_was_down_is_not_cached(make_client):
    llm = FlakyLLM()
    client = make_client(llm=llm)
    pid = load_demo(client, "P03")
    down = client.post(f"/api/profiles/{pid}/reports").json()
    assert down["passed"] is False and down["violations"][0]["code"] == "llm_error"
    assert down["content"]["summary"]  # the template fallback is still shown
    llm.up = True
    again = client.post(f"/api/profiles/{pid}/reports").json()
    assert again["id"] != down["id"] and again["passed"] is True and again["model"] == "echo-llm"
    assert client.post(f"/api/profiles/{pid}/reports").json()["id"] == again["id"]  # a good one is cached


def test_changing_trades_creates_a_new_report(client, synthetic_store):
    pid = load_demo(client, "P03")
    first = client.post(f"/api/profiles/{pid}/reports").json()["id"]
    a = first_trading_days(synthetic_store, 1)[0]
    price = int(synthetic_store.bar("FPT", synthetic_store.trading_days[10]).close // 10 * 10)
    upload(client, pid, f"trade_date,symbol,side,quantity,price\n{a},FPT,BUY,100,{price}\n")
    second = client.post(f"/api/profiles/{pid}/reports").json()["id"]
    assert first != second


def test_latest_report_404_then_found(client):
    pid = load_demo(client, "P03")
    assert client.get(f"/api/profiles/{pid}/reports/latest").status_code == 404
    rid = client.post(f"/api/profiles/{pid}/reports").json()["id"]
    assert client.get(f"/api/profiles/{pid}/reports/latest").json()["id"] == rid


def test_report_without_llm_configured_is_503(make_client):
    client = make_client(llm=None)
    pid = load_demo(client, "P03")
    r = client.post(f"/api/profiles/{pid}/reports")
    assert r.status_code == 503 and "LLM" in r.json()["detail"]


def test_bad_llm_output_still_returns_a_report_marked_not_passed(make_client):
    client = make_client(llm=FakeLLM([{"garbage": True}]))
    pid = load_demo(client, "P03")
    r = client.post(f"/api/profiles/{pid}/reports")
    assert r.status_code == 200 and r.json()["passed"] is False and r.json()["violations"]
    assert len(r.json()["content"]["insights"]) >= 1


# ---------------------------------------------------------------- chart data and thresholds
def test_portfolio_view_has_rebased_series_and_weights(client):
    pid = load_demo(client, "P03")
    view = client.get(f"/api/profiles/{pid}/portfolio").json()
    assert view["rebased"][0]["portfolio"] == 100 and view["rebased"][0]["benchmark"] == 100
    assert len(view["rebased"]) > 50
    assert abs(sum(view["weights_symbol"].values()) - 1) < 1e-9 or view["weights_symbol"] == {}
    assert set(view) >= {"first_date", "last_date", "rebased", "weights_symbol", "weights_sector"}


def test_portfolio_view_without_trades_is_409(client):
    pid = new_profile(client)
    assert client.get(f"/api/profiles/{pid}/portfolio").status_code == 409


def test_thresholds_endpoint_exposes_the_config_the_ui_displays(client):
    t = client.get("/api/thresholds").json()
    assert t["formula_version"] and t["concentration"]["hhi_warn"] == 0.25 and "balanced" in t["risk_tiers"]


# ---------------------------------------------------------------- articles
def test_articles_returns_three_matching_the_flags(client):
    pid = load_demo(client, "P03")
    arts = client.get(f"/api/profiles/{pid}/articles").json()
    assert len(arts) == 3 and any("disposition" in a["tags"] for a in arts)


def test_articles_without_trades_are_general(client):
    pid = new_profile(client)
    arts = client.get(f"/api/profiles/{pid}/articles").json()
    assert len(arts) == 3 and all("general" in a["tags"] for a in arts)


# ---------------------------------------------------------------- misc
def test_cors_allows_the_configured_origin(make_client):
    client = make_client(cors="https://app.example.com")
    r = client.options("/api/health", headers={"Origin": "https://app.example.com",
                                               "Access-Control-Request-Method": "GET"})
    assert r.headers.get("access-control-allow-origin") == "https://app.example.com"


def test_unknown_profile_on_every_profile_route_is_404(client):
    ghost = "00000000-0000-0000-0000-000000000000"
    for method, path in [("get", "trades"), ("get", "metrics"), ("get", "portfolio"), ("post", "reports"),
                         ("get", "reports/latest"), ("get", "articles")]:
        r = getattr(client, method)(f"/api/profiles/{ghost}/{path}")
        assert r.status_code == 404, path
