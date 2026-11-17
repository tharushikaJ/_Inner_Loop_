const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "/api").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function errorMessage(detail, status) {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length) {
    return detail.map((item) => item.msg).filter(Boolean).join(" ") || "Please check the form and try again.";
  }
  if (status === 401) return "Your session has expired. Please sign in again.";
  if (status === 403) return "You do not have permission to perform this action.";
  if (status === 404) return "The requested record was not found.";
  if (status === 422) return "Please check the submitted information and try again.";
  if (status >= 500) return "The InnerLoop API encountered an error. Please try again.";
  return "Something went wrong. Please try again.";
}

export async function apiRequest(path, options = {}) {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      credentials: "include",
      headers: {
        Accept: "application/json",
        ...(options.body ? { "Content-Type": "application/json" } : {}),
        ...options.headers,
      },
    });
  } catch {
    throw new ApiError("Cannot reach the InnerLoop API. Confirm the backend is running and try again.", 0);
  }

  const data = response.status === 204 ? null : await response.json().catch(() => null);
  if (!response.ok) throw new ApiError(errorMessage(data?.detail, response.status), response.status);
  return data;
}

export const authApi = {
  login: (credentials) => apiRequest("/auth/login", { method: "POST", body: JSON.stringify(credentials) }),
  microsoftLogin: (idToken) => apiRequest("/auth/microsoft", { method: "POST", body: JSON.stringify({ id_token: idToken }) }),
  register: (details) => apiRequest("/auth/register", { method: "POST", body: JSON.stringify(details) }),
  supervisors: () => apiRequest("/auth/supervisors"),
  me: () => apiRequest("/auth/me"),
  logout: () => apiRequest("/auth/logout", { method: "POST" }),
};
