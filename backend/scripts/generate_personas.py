"""Generate labeled synthetic trade histories with known behaviors (for demo and evaluation).

    uv run python scripts/generate_personas.py --seeds 3

Reads only `persona_specs.yaml` and the price files. Output is deterministic per (persona, seed).
Fees and taxes are left blank in the CSV: they are applied when the file is loaded.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Annotated

import numpy as np
import yaml
from pydantic import AfterValidator, BaseModel, ConfigDict

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.core.prices import INDEX_SYMBOL, PriceStore

LOT = 100
PRICE_TICK = 10


def _check_range(r: tuple[float, float]) -> tuple[float, float]:
    if r[0] > r[1]:
        raise ValueError(f"range lo > hi: {r}")
    return r


Range = Annotated[tuple[float, float], AfterValidator(_check_range)]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Common(Strict):
    capital: Range
    price_noise: Range
    warmup_sessions: int
    fee_reserve: float
    sell_cost: float
    universe: list[str]


class PersonaSpec(Strict):
    id: str
    title: str
    description: str
    tier: str
    answers: list[int]
    labels: list[str]
    behaviors: list[str]
    pool: list[str] = []
    params: dict[str, Range] = {}


class Specs(Strict):
    common: Common
    personas: list[PersonaSpec]


def load_specs(path: Path) -> Specs:
    return Specs.model_validate(yaml.safe_load(Path(path).read_text(encoding="utf-8")))


# ------------------------------------------------------------------ simulator
class Sim:
    """Cash + share counts over the trading calendar. Every trade is a round-lot at a noisy real price."""

    def __init__(self, store: PriceStore, common: Common, rng: np.random.Generator):
        self.store, self.c, self.rng = store, common, rng
        self.days = store.trading_days
        self.capital = float(rng.uniform(*common.capital))
        self.cash = self.capital
        self.held: dict[str, int] = {}
        self.entry: dict[str, float] = {}
        self.rows: list[tuple] = []
        self.close_arr = {s: store.close_series(s).to_numpy(dtype=float) for s in store.symbols}

    def u(self, rng_pair: Range) -> float:
        return float(self.rng.uniform(*rng_pair))

    def ui(self, rng_pair: Range) -> int:
        return int(self.rng.integers(int(rng_pair[0]), int(rng_pair[1]) + 1))

    def close(self, sym: str, i: int) -> float:
        return float(self.close_arr[sym][i])

    def rise(self, sym: str, i: int, lookback: int = 5) -> float:
        """Rise of the previous session's close over the `lookback` sessions before it."""
        if i - 1 - lookback < 0:
            return 0.0
        a = self.close_arr[sym]
        return float(a[i - 1] / a[i - 1 - lookback] - 1)

    def equity(self, i: int) -> float:
        return self.cash + sum(q * self.close(s, i) for s, q in self.held.items())

    def holdings_value(self, i: int) -> float:
        return sum(q * self.close(s, i) for s, q in self.held.items())

    def _price(self, sym: str, i: int) -> int:
        bar = self.store.bar(sym, self.days[i])
        p = min(max(bar.close * self.rng.uniform(*self.c.price_noise), bar.low), bar.high)
        return max(PRICE_TICK, int(round(p / PRICE_TICK) * PRICE_TICK))

    def buy(self, sym: str, i: int, value: float) -> int:
        """Buy round lots worth about `value`, never spending cash that is not there. Returns shares."""
        price = self._price(sym, i)
        budget = min(value, self.cash)
        lots = int(budget / (price * (1 + self.c.fee_reserve)) // LOT)
        if lots < 1:
            return 0
        qty = lots * LOT
        self.cash -= qty * price * (1 + self.c.fee_reserve)
        old = self.held.get(sym, 0)
        self.entry[sym] = (self.entry.get(sym, 0.0) * old + price * qty) / (old + qty)
        self.held[sym] = old + qty
        self.rows.append((self.days[i], sym, "BUY", qty, price))
        return qty

    def sell(self, sym: str, i: int, qty: int) -> int:
        qty = min(qty - qty % LOT, self.held.get(sym, 0))
        if qty < LOT:
            return 0
        price = self._price(sym, i)
        self.cash += qty * price * (1 - self.c.sell_cost)
        self.held[sym] -= qty
        if self.held[sym] == 0:
            del self.held[sym]
            self.entry.pop(sym, None)
        self.rows.append((self.days[i], sym, "SELL", qty, price))
        return qty

    def is_first_session_of_month(self, i: int) -> bool:
        return i == 0 or self.days[i].month != self.days[i - 1].month


Step = Callable[[int], None]


def _pool(sim: Sim, spec: PersonaSpec, k: int | None = None) -> list[str]:
    pool = spec.pool or [s for s in sim.c.universe if s in sim.store.symbols]
    if k is None or k >= len(pool):
        return list(pool)
    return [str(x) for x in sim.rng.choice(pool, size=k, replace=False)]


# ------------------------------------------------------------------ behaviors (each returns a daily step)
def make_overtrading(sim: Sim, spec: PersonaSpec, disposition_exit: bool) -> Step:
    p = spec.params
    p_entry = sim.u(p["trades_per_month"]) / 2 / 21  # round trips per session
    size, stop = sim.u(p["size_pct"]), (sim.u(p["loss_stop"]) if "loss_stop" in p else 0.25)
    pool = _pool(sim, spec, sim.ui(p["pool_size"]))
    lots: list[dict] = []

    def step(i: int) -> None:
        for lot in list(lots):
            if i < lot["exit"]:
                continue
            cur = sim.close(lot["sym"], i)
            winner = cur >= lot["entry"]
            may_sell = (not disposition_exit) or winner or cur / lot["entry"] - 1 <= -stop
            if may_sell and sim.sell(lot["sym"], i, lot["qty"]):
                lots.remove(lot)
        if sim.rng.random() < p_entry:
            sym = str(sim.rng.choice(pool))
            qty = sim.buy(sym, i, size * sim.equity(i))
            if qty:
                lots.append({"sym": sym, "qty": qty, "entry": sim.close(sym, i),
                             "exit": i + sim.ui(p["hold_sessions"])})

    return step


def make_disposition(sim: Sim, spec: PersonaSpec) -> Step:
    p = spec.params
    slots, stop, entry_prob = sim.ui(p["slots"]), sim.u(p["loss_stop"]), sim.u(p["entry_prob"])
    slot_value = sim.capital / slots
    targets: dict[str, float] = {}
    universe = _pool(sim, spec)

    def step(i: int) -> None:
        for sym in list(sim.held):
            gain = sim.close(sym, i) / sim.entry[sym] - 1
            if gain >= targets[sym] or gain <= -stop:
                sim.sell(sym, i, sim.held[sym])
                targets.pop(sym, None)
        if len(sim.held) < slots and sim.rng.random() < entry_prob:
            free = [s for s in universe if s not in sim.held]
            if free:
                sym = str(sim.rng.choice(free))
                if sim.buy(sym, i, slot_value):
                    targets[sym] = sim.u(p["win_target"])

    return step


# A chaser waits for a hot stock before buying. On real prices the longest stretch without any 10%
# five-session riser was 35 sessions (2025-11..2026-10), so 15 made most chasing buys silently drop.
CHASE_WAIT_SESSIONS = 40


def make_chasing(sim: Sim, spec: PersonaSpec) -> Step:
    p = spec.params
    share, size = sim.u(p["chase_share"]), sim.u(p["size_pct"]) * sim.capital
    universe = _pool(sim, spec)
    state = {"due": 0, "pending": None}

    def step(i: int) -> None:
        if i < state["due"]:
            return
        if state["pending"] is None:
            state["pending"] = {"chase": sim.rng.random() < share, "deadline": i + CHASE_WAIT_SESSIONS,
                                "threshold": sim.u(p["rise"])}
        job = state["pending"]
        if job["chase"]:
            cands = [s for s in universe if sim.rise(s, i) >= job["threshold"]]
            if not cands and i < job["deadline"]:
                return  # wait for a hot stock
            pick = cands
        else:
            pick = [s for s in universe if sim.rise(s, i) < 0.04]
        if pick:
            sim.buy(str(sim.rng.choice(pick)), i, size)
        state["pending"], state["due"] = None, i + sim.ui(p["interval_sessions"])

    return step


def make_concentration(sim: Sim, spec: PersonaSpec) -> Step:
    p = spec.params
    weight, n_other = sim.u(p["main_weight"]), sim.ui(p["other_count"])
    invest = sim.u(p["invest_fraction"]) * sim.capital
    symbols = _pool(sim, spec, 1 + n_other)
    main, others = symbols[0], symbols[1:]
    rebalance_prob = sim.u(p["rebalance_prob"]) if "rebalance_prob" in p else 1.0
    state = {"started": False}

    def step(i: int) -> None:
        if not state["started"]:
            sim.buy(main, i, weight * invest)
            for s in others:
                sim.buy(s, i, (1 - weight) * invest / len(others))
            state["started"] = True
        elif sim.is_first_session_of_month(i) and sim.rng.random() < rebalance_prob:
            held = sim.holdings_value(i)
            main_value = sim.held.get(main, 0) * sim.close(main, i)
            others_value = held - main_value
            diff = weight * others_value / (1 - weight) - main_value
            if abs(diff) > 0.02 * held:
                if diff > 0:
                    sim.buy(main, i, diff)
                else:
                    sim.sell(main, i, int(-diff / sim.close(main, i)))

    return step


def make_risk_mismatch(sim: Sim, spec: PersonaSpec) -> Step:
    p = spec.params
    symbols = _pool(sim, spec, sim.ui(p["stock_count"]))
    invest = sim.u(p["invest_fraction"]) * sim.capital
    top_pct, started = sim.u(p["top_up_pct"]), {"v": False}

    def step(i: int) -> None:
        if not started["v"]:
            for s in symbols:
                sim.buy(s, i, invest / len(symbols))
            started["v"] = True
        elif sim.is_first_session_of_month(i):
            for _ in range(sim.ui(p["top_ups_per_month"])):
                sim.buy(str(sim.rng.choice(symbols)), i, top_pct * sim.capital)

    return step


def make_dca(sim: Sim, spec: PersonaSpec) -> Step:
    frac = sim.u(spec.params["monthly_fraction"])
    symbols = _pool(sim, spec)
    # Each stock has its own monthly budget; what a round lot could not use carries over, otherwise a
    # stock whose lot costs more than one month's slice would never be bought.
    budget = dict.fromkeys(symbols, 0.0)

    def step(i: int) -> None:
        if sim.is_first_session_of_month(i):
            for s in symbols:
                budget[s] += frac * sim.capital / len(symbols)
                cash_before = sim.cash
                if sim.buy(s, i, budget[s]):
                    budget[s] -= cash_before - sim.cash

    return step


def make_rebalance(sim: Sim, spec: PersonaSpec) -> Step:
    p = spec.params
    symbols = _pool(sim, spec, sim.ui(p["stock_count"]))
    invest, every = sim.u(p["invest_fraction"]) * sim.capital, sim.ui(p["rebalance_every_sessions"])
    state = {"start": None}

    def step(i: int) -> None:
        if state["start"] is None:
            for s in symbols:
                sim.buy(s, i, invest / len(symbols))
            state["start"] = i
        elif (i - state["start"]) % every == 0:
            total = sim.holdings_value(i)
            target = total / len(symbols)
            diffs = {s: target - sim.held.get(s, 0) * sim.close(s, i) for s in symbols}
            for s, diff in diffs.items():  # sell overweights first to fund the buys
                if diff < -0.03 * target:
                    sim.sell(s, i, int(-diff / sim.close(s, i)))
            for s, diff in diffs.items():
                if diff > 0.03 * target:
                    sim.buy(s, i, diff)

    return step


def make_few_trades(sim: Sim, spec: PersonaSpec, first: int) -> Step:
    """Six BUYs of six different stocks: too few trades to judge, and not accidentally concentrated."""
    size = sim.u(spec.params["size_pct"]) * sim.capital
    when = sorted(int(x) for x in sim.rng.choice(np.arange(first, len(sim.days)), size=6, replace=False))
    plan = dict(zip(when, _pool(sim, spec, 6), strict=True))

    def step(i: int) -> None:
        if i in plan:
            sim.buy(plan[i], i, size)

    return step


def make_herding(sim: Sim, spec: PersonaSpec, first: int) -> Step:
    p = spec.params
    symbols = _pool(sim, spec, sim.ui(p["pool_size"]))
    frac = sim.u(p["monthly_fraction"])
    index = sim.close_arr[INDEX_SYMBOL]
    drop = sim.u(p["index_drop"])
    panic = {j for j in range(max(first, 1), len(sim.days)) if index[j] / index[j - 1] - 1 <= drop}
    panic |= {j + 1 for j in panic if j + 1 < len(sim.days)}
    calm = [j for j in range(first + 20, len(sim.days)) if j not in panic]
    panic_days = sorted(j for j in panic if j >= first + 20)
    n_events, share = sim.ui(p["sell_events"]), sim.u(p["herd_share"])
    n_herd = round(n_events * share) if panic_days else 0
    events: dict[int, int] = {}
    for j in [int(x) for x in sim.rng.choice(panic_days, size=n_herd)] if n_herd else []:
        events[j] = events.get(j, 0) + 1
    for j in [int(x) for x in sim.rng.choice(calm, size=n_events - n_herd)]:
        events[j] = events.get(j, 0) + 1
    sell_frac = p["sell_fraction"]

    def step(i: int) -> None:
        if sim.is_first_session_of_month(i) or i == first:
            for s in symbols:
                sim.buy(s, i, frac * sim.capital / len(symbols))
        for _ in range(events.get(i, 0)):
            held = [s for s, q in sim.held.items() if q >= LOT]
            if held:
                sym = str(sim.rng.choice(held))
                sim.sell(sym, i, max(LOT, int(sim.held[sym] * sim.u(sell_frac))))

    return step


# ------------------------------------------------------------------ assembly
def build_steps(sim: Sim, spec: PersonaSpec, first: int) -> list[Step]:
    b = set(spec.behaviors)
    if b == {"overtrading"}:
        return [make_overtrading(sim, spec, disposition_exit=False)]
    if b == {"overtrading", "disposition"}:
        return [make_overtrading(sim, spec, disposition_exit=True)]
    if b == {"disposition"}:
        return [make_disposition(sim, spec)]
    if b == {"chasing"}:
        return [make_chasing(sim, spec)]
    if b == {"concentration"}:
        return [make_concentration(sim, spec)]
    if b == {"concentration", "chasing"}:
        return [make_concentration(sim, spec), make_chasing(sim, spec)]
    if b == {"risk_mismatch"}:
        return [make_risk_mismatch(sim, spec)]
    if b == {"dca"}:
        return [make_dca(sim, spec)]
    if b == {"rebalance"}:
        return [make_rebalance(sim, spec)]
    if b == {"few_trades"}:
        return [make_few_trades(sim, spec, first)]
    if b == {"herding"}:
        return [make_herding(sim, spec, first)]
    raise ValueError(f"{spec.id}: unknown behavior combination {sorted(b)}")


def generate_one(store: PriceStore, specs: Specs, spec: PersonaSpec, seed: int) -> list[tuple]:
    rng = np.random.default_rng([seed, int(spec.id[1:])])
    sim = Sim(store, specs.common, rng)
    first = specs.common.warmup_sessions
    steps = build_steps(sim, spec, first)
    for i in range(first, len(sim.days)):
        for step in steps:
            step(i)
    return sim.rows


def write_csv(rows: list[tuple], path: Path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["trade_date", "symbol", "side", "quantity", "price", "fee", "tax"])
        for d, sym, side, qty, price in rows:
            w.writerow([d.isoformat(), sym, side, qty, price, "", ""])


def generate_all(store: PriceStore, specs: Specs, seeds: int, out_dir: Path) -> None:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    labels: dict[str, list[str]] = {}
    for spec in specs.personas:
        for seed in range(1, seeds + 1):
            rows = generate_one(store, specs, spec, seed)
            write_csv(rows, out_dir / f"{spec.id}_s{seed}.csv")
            labels[f"{spec.id}_s{seed}"] = spec.labels
    dump = lambda name, obj: (out_dir / name).write_text(
        json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    dump("labels.json", labels)
    dump("answers.json", {s.id: s.answers for s in specs.personas})
    dump("personas.json", [{"persona_id": s.id, "title": s.title, "tier": s.tier,
                            "description": s.description, "labels": s.labels} for s in specs.personas])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--prices", default=str(ROOT / "data" / "prices"))
    ap.add_argument("--specs", default=str(Path(__file__).with_name("persona_specs.yaml")))
    ap.add_argument("--out", default=str(ROOT / "data" / "personas"))
    args = ap.parse_args()
    specs = load_specs(Path(args.specs))
    generate_all(PriceStore(Path(args.prices)), specs, args.seeds, Path(args.out))
    print(f"wrote {len(specs.personas)} personas x {args.seeds} seeds to {args.out}")


if __name__ == "__main__":
    main()
