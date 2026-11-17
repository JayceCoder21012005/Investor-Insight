// The only place the frontend talks to the backend. Types come from the generated OpenAPI file.
import type { components } from "./api-types";

type S = components["schemas"];
export type Metrics = S["Metrics"];
export type Thresholds = S["Thresholds"];
export type PortfolioView = S["PortfolioView"];
export type ReportOut = S["ReportOut"];
export type Article = S["Article"];
export type DemoItem = S["DemoItem"];
export type ProfileOut = S["ProfileOut"];
export type ValidationResult = S["ValidationResult"];
export type RowIssue = S["RowIssue"];
export type Flag = S["Flag"];

const base = () => (process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000").replace(/\/$/, "");
const url = (path: string) => `${base()}/api${path}`;

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function failure(res: Response): Promise<ApiError> {
  let message = `Đã xảy ra lỗi (mã ${res.status}). Vui lòng thử lại.`;
  try {
    const body = await res.json();
    if (typeof body?.detail === "string") message = body.detail;
  } catch {
    /* body was not JSON: keep the generic message */
  }
  return new ApiError(res.status, message);
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(url(path), init);
  } catch {
    throw new ApiError(0, "Không kết nối được tới máy chủ. Vui lòng kiểm tra mạng và thử lại.");
  }
  if (!res.ok) throw await failure(res);
  return (await res.json()) as T;
}

const post = <T>(path: string, body?: unknown) =>
  request<T>(path, {
    method: "POST",
    ...(body === undefined
      ? {}
      : { headers: { "content-type": "application/json" }, body: JSON.stringify(body) }),
  });

export type UploadOutcome = { ok: boolean; result: ValidationResult };

export const api = {
  listDemo: () => request<DemoItem[]>("/demo"),
  loadDemo: (personaId: string) => post<{ id: string }>(`/demo/${personaId}/load`),
  createProfile: (answers: number[]) => post<ProfileOut>("/profiles", { answers }),
  getThresholds: () => request<Thresholds>("/thresholds"),
  getMetrics: (id: string) => request<Metrics>(`/profiles/${id}/metrics`),
  getPortfolio: (id: string) => request<PortfolioView>(`/profiles/${id}/portfolio`),
  getArticles: (id: string) => request<Article[]>(`/profiles/${id}/articles`),
  createReport: (id: string) => post<ReportOut>(`/profiles/${id}/reports`),

  async getLatestReport(id: string): Promise<ReportOut | null> {
    try {
      return await request<ReportOut>(`/profiles/${id}/reports/latest`);
    } catch (e) {
      if (e instanceof ApiError && e.status === 404) return null;
      throw e;
    }
  },

  /** A rejected file (422) is a normal outcome with row-level messages, so it is returned, not thrown. */
  async uploadTrades(id: string, file: File): Promise<UploadOutcome> {
    const form = new FormData();
    form.append("file", file);
    let res: Response;
    try {
      res = await fetch(url(`/profiles/${id}/trades`), { method: "POST", body: form });
    } catch {
      throw new ApiError(0, "Không kết nối được tới máy chủ. Vui lòng kiểm tra mạng và thử lại.");
    }
    if (res.status === 200 || res.status === 422) {
      return { ok: res.status === 200, result: (await res.json()) as ValidationResult };
    }
    throw await failure(res);
  },
};

export const templateCsvUrl = () => url("/template.csv");
