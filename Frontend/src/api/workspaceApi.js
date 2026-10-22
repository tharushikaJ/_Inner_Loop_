import { apiRequest } from "./authApi";

export const workspaceApi = {
  dashboard: () => apiRequest("/dashboard"),
  projects: () => apiRequest("/projects"),
  tasks: () => apiRequest("/tasks"),
  meetings: () => apiRequest("/meetings"),
  meetingRooms: () => apiRequest("/meeting-rooms"),
  reportSummary: () => apiRequest("/reports/summary"),
  users: () => apiRequest("/users"),
  supervisors: () => apiRequest("/users/supervisors"),
  updateUser: (userId, details) => apiRequest(`/users/${userId}`, { method: "PATCH", body: JSON.stringify(details) }),
  auditLogs: () => apiRequest("/audit-logs"),
  settings: () => apiRequest("/settings"),
};
