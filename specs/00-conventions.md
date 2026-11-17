# 00 — Conventions

## Rules
- Every number shown to users comes from `backend/app/core`. The LLM never computes or invents numbers.
- Every threshold lives in `backend/config/thresholds.yaml`. No magic numbers in code.
- UI text and LLM output in Vietnamese. Code, comments, identifiers in English.
- Money in VND as `int` (ledger) or `Decimal`; never float inside the ledger. Dates `YYYY-MM-DD`.
- Each core function has a unit test with a hand-computed expected value.
- `backend/app/core` is pure: no DB, no HTTP, no LLM. Input DataFrames/pydantic, output pydantic.
- Out of scope: auth, real brokerage connection, price prediction, derivatives, margin, dividends/splits.

## Stack
- Backend: Python 3.11, FastAPI, pandas, pydantic v2, pydantic-settings, SQLModel, Alembic, psycopg 3.
- Python tooling: uv only. No pip, no requirements.txt.
- Database: PostgreSQL on Neon (see 06).
- Frontend: Next.js App Router, TypeScript, Tailwind, shadcn/ui, Recharts.
- LLM: one provider behind `LLMClient` (see 08).

## Layout
```
backend/
  app/main.py, config.py, db.py, models.py, schemas.py
  app/core/{prices,validate,fees,ledger,portfolio,metrics,flags,risk}.py
  app/ai/{llm,prompts,guardrails,templates,report,recommend}.py
  app/api/{profiles,trades,reports,demo}.py
  config/thresholds.yaml
  content/articles/*.md
  data/prices/*.parquet, data/sectors.json, data/personas/
  migrations/                     # Alembic
  scripts/{fetch_prices,generate_personas,run_eval}.py, persona_specs.yaml
  tests/
frontend/
eval/
```

## Environment
| var | used by |
|---|---|
| `DATABASE_URL` | app runtime, Neon pooled string |
| `DATABASE_URL_DIRECT` | Alembic migrations, Neon direct string |
| `TEST_DATABASE_URL` | API tests, Neon `test` branch |
| `LLM_API_KEY`, `LLM_MODEL` | `ai/llm.py` |
| `NEXT_PUBLIC_API_BASE` | frontend |

`config.py`: `Settings(BaseSettings)` reads env (`.env` locally); `Thresholds(BaseModel)` mirrors thresholds.yaml field by field and is validated at startup. Invalid config → app refuses to start.

## uv
```bash
uv init backend --python 3.11            # once
uv add fastapi "uvicorn[standard]" pandas pyarrow pydantic pydantic-settings \
       sqlmodel alembic "psycopg[binary]" python-multipart pyyaml vnstock
uv add --dev pytest ruff
uv sync                                    # install from uv.lock
uv run pytest
uv run uvicorn app.main:app --reload
uv run python scripts/<name>.py
```
Commit `pyproject.toml` and `uv.lock`. Every command in other specs runs through `uv run`.

## Pydantic rules
Pydantic models are the contract between every layer: CSV → core → DB → AI → API.
- All models in `app/schemas.py`, grouped by spec. Base class:
  ```python
  class Model(BaseModel):
      model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)
  ```
- Closed sets are `StrEnum`: `Side(BUY, SELL)`, `Tier(conservative, balanced, growth)`, `Level(beginner, intermediate, experienced)`, `FlagId(...)`.
- Constraints via `Annotated` + `Field`, reused as named types:
  ```python
  VND = Annotated[int, Field(ge=0)]
  PositiveQty = Annotated[int, Field(gt=0)]
  Ratio = Annotated[float, Field(ge=0, le=1)]
  Symbol = Annotated[str, StringConstraints(pattern=r"^[A-Z0-9]{3,10}$", to_upper=True)]
  ```
- Cross-field rules use `@model_validator(mode="after")` (e.g. SELL must have tax set after fees are applied).
- Parse at the edge, trust inside: validate once when data enters (CSV upload, LLM output, config, API body); core functions accept models, never raw dicts.
- LLM output schema = `Report.model_json_schema()`; parse with `Report.model_validate_json`.
- API request/response types are these models; FastAPI generates OpenAPI from them; frontend types are generated from OpenAPI (see 10).
- DB tables (SQLModel) are separate from API models; convert explicitly.
