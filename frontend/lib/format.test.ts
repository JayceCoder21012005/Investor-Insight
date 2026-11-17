import { describe, expect, it } from "vitest";
import { formatDate, formatNumber, formatPercent, formatVnd } from "./format";

describe("formatPercent", () => {
  it("uses a decimal comma and one decimal by default", () => {
    expect(formatPercent(0.385)).toBe("38,5%");
    expect(formatPercent(0.1)).toBe("10,0%");
  });
  it("keeps the sign of negative returns", () => {
    expect(formatPercent(-0.0523)).toBe("-5,2%");
  });
  it("supports other digit counts", () => {
    expect(formatPercent(1.5, 0)).toBe("150%");
  });
  it("shows a dash for missing values", () => {
    expect(formatPercent(null)).toBe("—");
    expect(formatPercent(undefined)).toBe("—");
  });
});

describe("formatNumber", () => {
  it("uses vi-VN separators", () => {
    expect(formatNumber(1234567.891, 2)).toBe("1.234.567,89");
    expect(formatNumber(0.38)).toBe("0,38");
  });
  it("shows a dash for missing values", () => {
    expect(formatNumber(null)).toBe("—");
  });
});

describe("formatVnd", () => {
  it("groups thousands with dots and adds the dong sign", () => {
    expect(formatVnd(12500000)).toContain("12.500.000");
    expect(formatVnd(12500000)).toContain("₫");
  });
  it("rounds to whole dong and handles negatives", () => {
    expect(formatVnd(-1234.6)).toContain("1.235");
    expect(formatVnd(-1234.6)).toContain("-");
  });
});

describe("formatDate", () => {
  it("turns ISO dates into dd/MM/yyyy", () => {
    expect(formatDate("2026-01-05")).toBe("05/01/2026");
  });
});
