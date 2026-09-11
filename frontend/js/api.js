const API_BASE = "/api";

function getCookie(name) {
  const match = document.cookie.match(new RegExp("(^| )" + name + "=([^;]+)"));
  return match ? decodeURIComponent(match[2]) : null;
}

class ApiError extends Error {
  constructor(status, detail) {
    super(typeof detail === "string" ? detail : JSON.stringify(detail));
    this.status = status;
    this.detail = detail;
  }
}

async function rawFetch(path, method, headers, body) {
  const response = await fetch(API_BASE + path, {
    method,
    headers,
    credentials: "include",
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (response.status === 204) return { response, payload: null };
  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json") ? await response.json() : await response.text();
  return { response, payload };
}

let refreshInFlight = null;

async function apiFetch(path, { method = "GET", body, headers = {}, _isRetry = false } = {}) {
  const finalHeaders = { ...headers };
  const isUnsafe = !["GET", "HEAD", "OPTIONS"].includes(method);

  if (body !== undefined) finalHeaders["Content-Type"] = "application/json";
  if (isUnsafe) {
    const csrf = getCookie("csrf_token");
    if (csrf) finalHeaders["X-CSRF-Token"] = csrf;
  }

  const { response, payload } = await rawFetch(path, method, finalHeaders, body);

  if (response.status === 401 && !_isRetry && path !== "/auth/login" && path !== "/auth/refresh") {
    // Access token likely expired mid-session — refresh once and replay the request.
    refreshInFlight = refreshInFlight || rawFetch("/auth/refresh", "POST", {}, undefined).finally(() => {
      refreshInFlight = null;
    });
    const { response: refreshResponse } = await refreshInFlight;
    if (refreshResponse.ok) {
      return apiFetch(path, { method, body, headers, _isRetry: true });
    }
  }

  if (!response.ok) {
    throw new ApiError(response.status, payload && payload.detail ? payload.detail : payload);
  }
  return payload;
}

const api = {
  get: (path) => apiFetch(path),
  post: (path, body, headers) => apiFetch(path, { method: "POST", body, headers }),
  patch: (path, body, headers) => apiFetch(path, { method: "PATCH", body, headers }),
  ApiError,
};

function newIdempotencyKey() {
  if (window.crypto && window.crypto.randomUUID) return window.crypto.randomUUID();
  return "idem-" + Date.now() + "-" + Math.random().toString(16).slice(2);
}
