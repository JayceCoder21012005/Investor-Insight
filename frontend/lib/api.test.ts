import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, api, templateCsvUrl } from "./api";

function mockFetch(status: number, body: unknown, contentType = "application/json") {
  const fn = vi.fn().mockResolvedValue(
    new Response(typeof body === "string" ? body : JSON.stringify(body), {
      status,
      headers: { "content-type": contentType },
    }),
  );
  vi.stubGlobal("fetch", fn);
  return fn;
}

afterEach(() => vi.unstubAllGlobals());

describe("api client", () => {
  it("prefixes /api to the configured base and parses JSON", async () => {
    const fn = mockFetch(200, [{ persona_id: "P01", title: "t", tier: "balanced", description: "d" }]);
    const demos = await api.listDemo();
    expect(demos[0].persona_id).toBe("P01");
    expect(String(fn.mock.calls[0][0])).toMatch(/\/api\/demo$/);
  });

  it("turns {detail} errors into ApiError with the Vietnamese message", async () => {
    mockFetch(409, { detail: "Chưa có dữ liệu giao dịch" });
    await expect(api.getMetrics("abc")).rejects.toMatchObject({
      status: 409,
      message: "Chưa có dữ liệu giao dịch",
    });
    await expect(api.getMetrics("abc")).rejects.toBeInstanceOf(ApiError);
  });

  it("falls back to a generic Vietnamese message when the body has no detail", async () => {
    mockFetch(500, "boom", "text/plain");
    await expect(api.getMetrics("abc")).rejects.toMatchObject({ status: 500 });
    await expect(api.getMetrics("abc")).rejects.toThrow(/lỗi/i);
  });

  it("returns the validation result (not an exception) when the upload is rejected with 422", async () => {
    const body = { rows: [], errors: [{ row: 2, field: "quantity", message: "Dòng 2: ..." }], warnings: [] };
    mockFetch(422, body);
    const res = await api.uploadTrades("abc", new File(["x"], "t.csv"));
    expect(res.ok).toBe(false);
    expect(res.result.errors[0].row).toBe(2);
  });

  it("returns ok:true with warnings for a successful upload", async () => {
    mockFetch(200, { rows: [], errors: [], warnings: [{ row: 1, field: "price", message: "w" }] });
    const res = await api.uploadTrades("abc", new File(["x"], "t.csv"));
    expect(res.ok).toBe(true);
    expect(res.result.warnings).toHaveLength(1);
  });

  it("sends the upload as multipart form data without a manual content-type", async () => {
    const fn = mockFetch(200, { rows: [], errors: [], warnings: [] });
    await api.uploadTrades("abc", new File(["x"], "t.csv"));
    const init = fn.mock.calls[0][1] as RequestInit;
    expect(init.body).toBeInstanceOf(FormData);
    expect((init.headers as Record<string, string> | undefined)?.["content-type"]).toBeUndefined();
  });

  it("treats 404 on the latest report as 'no report yet'", async () => {
    mockFetch(404, { detail: "Chưa có báo cáo nào cho hồ sơ này" });
    expect(await api.getLatestReport("abc")).toBeNull();
  });

  it("still throws on other errors for the latest report", async () => {
    mockFetch(500, { detail: "x" });
    await expect(api.getLatestReport("abc")).rejects.toBeInstanceOf(ApiError);
  });

  it("posts the questionnaire answers as JSON", async () => {
    const fn = mockFetch(200, { id: "1", tier: "balanced", level: "beginner" });
    await api.createProfile([1, 2, 3, 4, 1]);
    const init = fn.mock.calls[0][1] as RequestInit;
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body as string)).toEqual({ answers: [1, 2, 3, 4, 1] });
  });

  it("exposes the sample CSV url", () => {
    expect(templateCsvUrl()).toMatch(/\/api\/template\.csv$/);
  });
});
