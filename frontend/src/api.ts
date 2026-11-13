import type {
  CaseSearchResult,
  DashboardSummary,
  ExtractionPreview,
  Vehicle,
  WorkOrder,
} from "./types";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: "İstek başarısız" }));
    throw new Error(payload.detail ?? "İstek başarısız");
  }

  return response.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string; service: string }>("/health"),
  dashboard: () => request<DashboardSummary>("/dashboard/summary"),
  listVehicles: () => request<Vehicle[]>("/vehicles"),
  createVehicle: (payload: Record<string, unknown>) =>
    request<Vehicle>("/vehicles", { method: "POST", body: JSON.stringify(payload) }),
  updateVehicle: (id: string, payload: Record<string, unknown>) =>
    request<Vehicle>(`/vehicles/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  listWorkOrders: () => request<WorkOrder[]>("/work-orders"),
  createWorkOrder: (payload: Record<string, unknown>) =>
    request<WorkOrder>("/work-orders", { method: "POST", body: JSON.stringify(payload) }),
  updateWorkOrder: (id: string, payload: Record<string, unknown>) =>
    request<WorkOrder>(`/work-orders/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  extractionPreview: (text: string) =>
    request<ExtractionPreview>("/ai/extract-preview", {
      method: "POST",
      body: JSON.stringify({ text }),
    }),
  searchCases: (query: string, dtcCode?: string) =>
    request<CaseSearchResult[]>("/cases/search", {
      method: "POST",
      body: JSON.stringify({ query, dtc_code: dtcCode || null, limit: 5 }),
    }),
};

