import type {
  CaseSearchResult,
  AIRuntimeStatus,
  DashboardSummary,
  ExtractionPreview,
  Vehicle,
  WorkOrder,
  TranscriptionResult,
} from "./types";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const isFormData = init?.body instanceof FormData;
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
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
  aiStatus: () => request<AIRuntimeStatus>("/ai/status"),
  transcribeAudio: (audio: Blob) => {
    const form = new FormData();
    const extension = audio.type.includes("ogg") ? "ogg" : audio.type.includes("wav") ? "wav" : audio.type.includes("flac") ? "flac" : "webm";
    form.append("audio", audio, `servis-kaydi.${extension}`);
    form.append("retain_audio", "false");
    return request<TranscriptionResult>("/audio/transcribe", { method: "POST", body: form });
  },
  searchCases: (
    query: string,
    dtcCode?: string,
    searchMode: "hybrid" | "keyword" | "semantic" = "hybrid",
  ) =>
    request<CaseSearchResult[]>("/cases/search", {
      method: "POST",
      body: JSON.stringify({
        query,
        dtc_code: dtcCode || null,
        limit: 6,
        search_mode: searchMode,
        approved_only: false,
      }),
    }),
};

