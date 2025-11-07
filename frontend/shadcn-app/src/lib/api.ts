export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:5001";

async function parseResponse(response: Response) {
  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    return response.json();
  }
  const text = await response.text();
  return text || null;
}

export async function apiRequest<T = any>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, options);
  const data = await parseResponse(response);
  if (!response.ok) {
    const message =
      (data && typeof data === "object" && "error" in data && data.error) ||
      (data && typeof data === "object" && "message" in data && data.message) ||
      (typeof data === "string" ? data : null) ||
      `请求失败（${response.status}）`;
    throw new Error(message as string);
  }
  return data as T;
}

export function apiJson<T = any>(
  path: string,
  payload?: Record<string, unknown>,
  init?: RequestInit
): Promise<T> {
  return apiRequest<T>(path, {
    ...init,
    method: init?.method ?? "POST",
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
    body: payload !== undefined ? JSON.stringify(payload) : undefined,
  });
}
