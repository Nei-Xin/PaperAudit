// Thin fetch wrapper.
// - VITE_USE_MOCK=1: GET requests read static JSON exported by
//   scripts/export_mock_api.py (local development without any server).
// - VITE_READ_ONLY=1: GET requests hit the real /api paths (served by
//   scripts/preview_server.py); writes are rejected in preview builds.

export const USE_MOCK = import.meta.env.VITE_USE_MOCK === "1";
export const READ_ONLY = USE_MOCK || import.meta.env.VITE_READ_ONLY === "1";

export class ApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
  }
}

function mockUrl(path: string): string {
  const clean = path.replace(/^\/api/, "").split("?")[0];
  return clean.endsWith("/pdf") ? `/mock-api${clean}` : `/mock-api${clean}.json`;
}

export function resourceUrl(path: string): string {
  return USE_MOCK ? mockUrl(path) : path;
}

export async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(resourceUrl(path), { headers: { Accept: "application/json" } });
  if (!response.ok) throw await toError(response);
  return (await response.json()) as T;
}

export async function send<T>(method: "POST" | "PUT" | "PATCH" | "DELETE", path: string, body?: unknown): Promise<T> {
  if (READ_ONLY) {
    throw new ApiError("当前为只读预览，修改不会保存。", 503);
  }
  const isForm = body instanceof FormData;
  const response = await fetch(path, {
    method,
    headers: isForm || body === undefined ? undefined : { "Content-Type": "application/json" },
    body: isForm ? body : body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) throw await toError(response);
  return response.status === 204 ? (undefined as T) : ((await response.json()) as T);
}

async function toError(response: Response): Promise<ApiError> {
  try {
    const payload = await response.json();
    return new ApiError(payload?.error?.message ?? response.statusText, response.status);
  } catch {
    return new ApiError(response.statusText || "请求失败", response.status);
  }
}

export const pdfUrl = (projectId: string) => resourceUrl(`/api/projects/${projectId}/pdf`);
