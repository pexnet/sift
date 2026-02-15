export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export type RequestOptions = Omit<RequestInit, "body" | "headers"> & {
  body?: unknown;
  headers?: Record<string, string>;
};

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/+$/, "") ?? "";

function resolveUrl(path: string): string {
  if (/^https?:\/\//i.test(path) || API_BASE_URL.length === 0) {
    return path;
  }

  return path.startsWith("/") ? `${API_BASE_URL}${path}` : `${API_BASE_URL}/${path}`;
}

async function parsePayload(response: Response): Promise<unknown> {
  if (response.status === 204) {
    return null;
  }

  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    return response.json() as Promise<unknown>;
  }

  const text = await response.text();
  return text.length > 0 ? text : null;
}

function buildHeaders(options: { headers?: Record<string, string>; body?: unknown }): Record<string, string> {
  const headers: Record<string, string> = {
    Accept: "application/json",
    ...options.headers,
  };

  if (options.body !== undefined && !(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  return headers;
}

async function request<TResponse>(url: string, options: RequestOptions = {}): Promise<TResponse> {
  const { body, headers, ...rest } = options;
  const normalizedHeaders = headers ? buildHeaders({ headers, body }) : buildHeaders({ body });
  const requestInit: RequestInit = {
    credentials: "include",
    ...rest,
    headers: normalizedHeaders,
  };

  if (body !== undefined) {
    requestInit.body = body instanceof FormData ? body : JSON.stringify(body);
  }

  const response = await fetch(resolveUrl(url), requestInit);

  const payload = await parsePayload(response);

  if (!response.ok) {
    const message =
      typeof payload === "object" && payload !== null && "detail" in payload && typeof payload.detail === "string"
        ? payload.detail
        : `Request failed with status ${response.status}`;

    throw new ApiError(message, response.status);
  }

  return payload as TResponse;
}

export const apiClient = {
  request<TResponse>(url: string, options: RequestOptions = {}) {
    return request<TResponse>(url, options);
  },
  get<TResponse>(url: string, options: RequestOptions = {}) {
    return request<TResponse>(url, { ...options, method: "GET" });
  },
  post<TRequest, TResponse>(url: string, body: TRequest, options: RequestOptions = {}) {
    return request<TResponse>(url, { ...options, method: "POST", body });
  },
  patch<TRequest, TResponse>(url: string, body: TRequest, options: RequestOptions = {}) {
    return request<TResponse>(url, { ...options, method: "PATCH", body });
  },
};
