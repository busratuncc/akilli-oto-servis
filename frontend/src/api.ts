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
  InventoryPart,
  InventorySummary,
  StockMovement,
  CardPaymentStartResult,
  CardChallenge,
  CardChallengeVerifyResult,
  EvaluationMode,
  EvaluationQuery,
  EvaluationRun,
  EvaluationSummary,
  EvidenceResponse,
  Appointment,
  AppointmentStatus,
  MaintenanceReminder,
  ReminderStatus,
  ScheduleSummary,
  InspectionCondition,
  InspectionReport,
  InspectionStatus,
  Estimate,
  EstimateSendResponse,
  PublicEstimate,
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
  getInvoice: (id: string) => request<Invoice>(`/invoices/${id}`),
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
  startTestCardPayment: (invoiceId: string, amount: string, cardLast4: string) =>
    request<CardPaymentStartResult>(`/invoices/${invoiceId}/card-payment/start`, {
      method: "POST",
      body: JSON.stringify({ amount, card_last4: cardLast4 }),
    }),
  testCardChallengeDetails: (challengeId: string, token: string) =>
    request<CardChallenge>(`/card-payment/challenges/${challengeId}/details`, {
      method: "POST",
      body: JSON.stringify({ token }),
    }),
  verifyTestCardChallenge: (challengeId: string, token: string, code: string) =>
    request<CardChallengeVerifyResult>(`/card-payment/challenges/${challengeId}/verify`, {
      method: "POST",
      body: JSON.stringify({ token, code }),
    }),
  listInventoryParts: () => request<InventoryPart[]>("/inventory/parts"),
  inventorySummary: () => request<InventorySummary>("/inventory/summary"),
  listStockMovements: () => request<StockMovement[]>("/inventory/movements"),
  createInventoryPart: (payload: Record<string, unknown>) =>
    request<InventoryPart>("/inventory/parts", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateInventoryPart: (id: string, payload: Record<string, unknown>) =>
    request<InventoryPart>(`/inventory/parts/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  recordStockMovement: (
    id: string,
    payload: { movement_type: "stock_in" | "stock_out"; quantity: string; notes: string | null },
  ) => request<InventoryPart>(`/inventory/parts/${id}/movements`, {
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
  evidenceAssistance: (
    query: string,
    dtcCode: string,
    searchMode: EvaluationMode,
  ) => request<EvidenceResponse>("/cases/evidence", {
    method: "POST",
    body: JSON.stringify({
      query,
      dtc_code: dtcCode || null,
      search_mode: searchMode,
    }),
  }),
  listEvaluationQueries: () => request<EvaluationQuery[]>("/evaluation/queries"),
  createEvaluationQuery: (payload: {
    name: string;
    query_text: string;
    dtc_code: string | null;
    expected_work_order_id: string;
    notes: string | null;
  }) => request<EvaluationQuery>("/evaluation/queries", {
    method: "POST",
    body: JSON.stringify(payload),
  }),
  deleteEvaluationQuery: (id: string) =>
    request<void>(`/evaluation/queries/${id}`, { method: "DELETE" }),
  listEvaluationRuns: () => request<EvaluationRun[]>("/evaluation/runs"),
  runEvaluation: (modes: EvaluationMode[], topK: number) =>
    request<EvaluationRun>("/evaluation/runs", {
      method: "POST",
      body: JSON.stringify({ modes, top_k: topK }),
    }),
  evaluationSummary: () => request<EvaluationSummary>("/evaluation/summary"),
  listAppointments: () => request<Appointment[]>("/appointments"),
  createAppointment: (payload: {
    vehicle_id: string;
    scheduled_start: string;
    scheduled_end: string;
    service_type: string;
    customer_complaint: string;
    assigned_technician: string | null;
    notes: string | null;
  }) => request<Appointment>("/appointments", {
    method: "POST",
    body: JSON.stringify(payload),
  }),
  updateAppointment: (id: string, payload: Partial<{
    vehicle_id: string;
    scheduled_start: string;
    scheduled_end: string;
    service_type: string;
    customer_complaint: string;
    status: AppointmentStatus;
    assigned_technician: string | null;
    notes: string | null;
  }>) => request<Appointment>(`/appointments/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  }),
  listMaintenanceReminders: () => request<MaintenanceReminder[]>("/maintenance-reminders"),
  createMaintenanceReminder: (payload: {
    vehicle_id: string;
    title: string;
    due_date: string | null;
    due_mileage: number | null;
    notes: string | null;
  }) => request<MaintenanceReminder>("/maintenance-reminders", {
    method: "POST",
    body: JSON.stringify(payload),
  }),
  updateMaintenanceReminder: (id: string, payload: Partial<{
    vehicle_id: string;
    title: string;
    due_date: string | null;
    due_mileage: number | null;
    status: ReminderStatus;
    notes: string | null;
  }>) => request<MaintenanceReminder>(`/maintenance-reminders/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  }),
  scheduleSummary: () => request<ScheduleSummary>("/schedule/summary"),
  listInspections: () => request<InspectionReport[]>("/inspections"),
  createInspection: (workOrderId: string) =>
    request<InspectionReport>(`/work-orders/${workOrderId}/inspection`, { method: "POST" }),
  updateInspection: (id: string, payload: {
    status?: InspectionStatus;
    odometer: number | null;
    technician_name: string | null;
    notes: string | null;
    mechanic_approved: boolean;
    items: Array<{
      item_key: string;
      condition: InspectionCondition;
      measurement: string | null;
      notes: string | null;
      resolved: boolean;
    }>;
  }) => request<InspectionReport>(`/inspections/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  }),
  listEstimates: () => request<Estimate[]>("/estimates"),
  createEstimate: (workOrderId: string, payload: {
    line_items: InvoiceCreatePayload["line_items"];
    discount_amount: string;
    tax_rate: string;
    notes: string | null;
    valid_until: string;
  }) => request<Estimate>(`/work-orders/${workOrderId}/estimates`, {
    method: "POST",
    body: JSON.stringify(payload),
  }),
  sendEstimate: (id: string) => request<EstimateSendResponse>(`/estimates/${id}/send`, {
    method: "POST",
  }),
  convertEstimateToInvoice: (id: string, dueDate: string | null) =>
    request<Invoice>(`/estimates/${id}/invoice`, {
      method: "POST",
      body: JSON.stringify({ due_date: dueDate }),
    }),
  publicEstimateDetails: (id: string, token: string) =>
    request<PublicEstimate>(`/public/estimates/${id}/details`, {
      method: "POST",
      body: JSON.stringify({ token }),
    }),
  publicEstimateDecision: (
    id: string,
    token: string,
    decision: "approved" | "rejected",
    note: string | null,
  ) => request<PublicEstimate>(`/public/estimates/${id}/decision`, {
    method: "POST",
    body: JSON.stringify({ token, decision, note }),
  }),
};

