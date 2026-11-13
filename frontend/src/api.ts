import type {
  CaseSearchResult,
  AIRuntimeStatus,
  DashboardSummary,
  ExtractionPreview,
  Vehicle,
  WorkOrder,
  TranscriptionResult,
  AuthMessage,
  AuthResponse,
  RegistrationPayload,
  ProfileUpdatePayload,
  AuditEvent,
  FinanceSummary,
  Invoice,
  InvoiceCreatePayload,
  PaymentCreatePayload,
} from "./types";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api";

export class ApiError extends Error {
  constructor(message: string, public status: number) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const isFormData = init?.body instanceof FormData;
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
      ...init?.headers,
    },
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: "İstek başarısız" }));
    throw new ApiError(payload.detail ?? "İstek başarısız", response.status);
  }

  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const api = {
  register: (payload: RegistrationPayload) =>
    request<AuthResponse>("/auth/register", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  requestOtp: (email: string, language: "tr" | "en") =>
    request<AuthMessage>("/auth/request-otp", {
      method: "POST",
      body: JSON.stringify({ email, language }),
    }),
  verifyOtp: (email: string, code: string, language: "tr" | "en") =>
    request<AuthResponse>("/auth/verify", {
      method: "POST",
      body: JSON.stringify({ email, code, language }),
    }),
  me: () => request<AuthResponse>("/auth/me"),
  logout: () => request<void>("/auth/logout", { method: "POST" }),
  updatePreferences: (preferredLanguage: "tr" | "en") =>
    request<AuthResponse>("/auth/preferences", {
      method: "PATCH",
      body: JSON.stringify({ preferred_language: preferredLanguage }),
    }),
  updateProfile: (payload: ProfileUpdatePayload) =>
    request<AuthResponse>("/auth/profile", {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  accountActivity: () => request<AuditEvent[]>("/auth/activity"),
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
  listInvoices: () => request<Invoice[]>("/invoices"),
  financeSummary: () => request<FinanceSummary>("/finance/summary"),
  createInvoice: (workOrderId: string, payload: InvoiceCreatePayload) =>
    request<Invoice>(`/work-orders/${workOrderId}/invoice`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  recordPayment: (invoiceId: string, payload: PaymentCreatePayload) =>
    request<Invoice>(`/invoices/${invoiceId}/payments`, {
      method: "POST",
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

