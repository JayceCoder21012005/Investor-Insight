import { describe, expect, it } from "vitest";
import { STATUS_LABEL, TENDENCIES, statusOf } from "./tendencies";
import type { components } from "./api-types";
import { METRICS, THRESHOLDS } from "./fixtures";

type Flag = components["schemas"]["Flag"];
const flag = (id: Flag["id"], keys: string[] = ["x.y"]): Flag => ({ id, severity: "warn", evidence_keys: keys });

describe("TENDENCIES", () => {
  it("lists the seven tendencies of the behavior tab, in spec order", () => {
    expect(TENDENCIES.map((t) => t.id)).toEqual([
      "overtrading",
      "concentration",
      "disposition",
      "chasing",
      "herding",
      "risk_mismatch",
      "overconfidence",
    ]);
  });
  it("gives every tendency a Vietnamese name and a formula for the 'Cách tính' popover", () => {
    for (const t of TENDENCIES) {
      expect(t.label.length).toBeGreaterThan(3);
      expect(t.formula.length).toBeGreaterThan(20);
    }
  });
  it("states the risk-mismatch volatility limit relative to the VN-Index of the same period", () => {
    const risk = TENDENCIES.find((t) => t.id === "risk_mismatch")!;
    // balanced: 1.6 x the index volatility 18% -> 29%
    const h = risk.headline(METRICS, THRESHOLDS);
    expect(h.threshold).toContain("1,6 lần VN-Index");
    expect(h.threshold).toContain("29%");
    expect(risk.inputs(METRICS).map((i) => i.label)).toContain("Độ biến động VN-Index cùng kỳ");
  });
});

describe("statusOf", () => {
  it("is 'attention' when the API raised the flag", () => {
    expect(statusOf("disposition", [flag("disposition")])).toBe("attention");
  });
  it("is 'ok' when nothing was raised", () => {
    expect(statusOf("concentration", [])).toBe("ok");
    expect(statusOf("disposition", [flag("chasing")])).toBe("ok");
  });
  it("is 'insufficient' when the API lacked enough sample for that tendency", () => {
    const f = flag("insufficient_data", ["disposition.n_sells", "herding.n_sells"]);
    expect(statusOf("disposition", [f])).toBe("insufficient");
    expect(statusOf("herding", [f])).toBe("insufficient");
    expect(statusOf("chasing", [f])).toBe("ok");
  });
  it("never reports insufficient for tendencies that have no sample gate", () => {
    const f = flag("insufficient_data", ["disposition.n_sells", "chasing.n_buys", "herding.n_sells"]);
    expect(statusOf("overtrading", [f])).toBe("ok");
    expect(statusOf("concentration", [f])).toBe("ok");
  });
  it("labels the three statuses in Vietnamese", () => {
    expect(STATUS_LABEL).toEqual({
      ok: "Bình thường",
      attention: "Cần chú ý",
      insufficient: "Chưa đủ dữ liệu",
    });
  });
});
