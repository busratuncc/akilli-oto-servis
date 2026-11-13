export type Vehicle = {
  id: string;
  anonymous_code: string;
  brand: string;
  model: string;
  model_year: number | null;
  engine: string | null;
  fuel_type: string | null;
  mileage: number | null;
  created_at: string;
};

export type DtcCode = {
  id?: string;
  code: string;
  description?: string | null;
};

export type WorkOrderStatus =
  | "draft"
  | "inspection"
  | "repairing"
  | "waiting_parts"
  | "completed"
  | "cancelled";

export type WorkOrder = {
  id: string;
  vehicle_id: string;
  customer_complaint: string;
  symptoms: string | null;
  diagnosis: string | null;
  actions: string | null;
  result: string | null;
  status: WorkOrderStatus;
  approved_by_mechanic: boolean;
  voice_transcript: string | null;
  created_at: string;
  dtc_codes: DtcCode[];
};

export type ExtractionPreview = {
  provider: string;
  raw_text: string;
  dtc_codes: string[];
  dtc_details: DtcCode[];
  mileage: number | null;
  probable_fields: Record<string, unknown>;
  warnings: string[];
};

export type CaseSearchResult = {
  work_order: WorkOrder;
  vehicle: Vehicle;
  match_reason: string;
  similarity_score: number | null;
  search_method: "keyword" | "semantic" | "hybrid" | "dtc";
};

export type TranscriptionResult = {
  transcript: string;
  language: string;
  language_probability: number;
  duration_seconds: number;
  provider: string;
  audio_retained: boolean;
};

export type AIRuntimeStatus = {
  embedding_model: string;
  embedding_loaded: boolean;
  embedding_error: string | null;
  whisper_model: string;
  whisper_loaded: boolean;
  whisper_error: string | null;
};

export type DashboardSummary = {
  total_vehicles: number;
  total_work_orders: number;
  open_work_orders: number;
  completed_work_orders: number;
  approved_cases: number;
  status_counts: Partial<Record<WorkOrderStatus, number>>;
  recent_work_orders: WorkOrder[];
};

export type AuthUser = {
  id: string;
  email: string;
  full_name: string;
  workshop_name: string | null;
  phone_country_code: string;
  phone_number: string;
  preferred_language: "tr" | "en";
  marketing_consent: boolean;
  created_at: string;
  privacy_accepted_at: string;
  terms_accepted_at: string;
};

export type ProfileUpdatePayload = {
  full_name: string;
  workshop_name: string | null;
  phone_country_code: string;
  phone_number: string;
  marketing_consent: boolean;
};

export type AuditEvent = {
  id: string;
  event_type: string;
  entity_type: string | null;
  entity_id: string | null;
  event_data: Record<string, unknown>;
  created_at: string;
};

export type RegistrationPayload = {
  full_name: string;
  workshop_name: string | null;
  email: string;
  phone_country_code: string;
  phone_number: string;
  preferred_language: "tr" | "en";
  privacy_accepted: true;
  terms_accepted: true;
  marketing_consent: boolean;
};

export type AuthResponse = {
  user: AuthUser;
  mailpit_url?: string | null;
};

export type AuthMessage = {
  message: string;
  retry_after?: number | null;
  mailpit_url?: string | null;
  local_code?: string | null;
};

export type InvoiceItemType = "part" | "labor" | "other";
export type InvoiceStatus = "issued" | "partially_paid" | "paid" | "cancelled";
export type PaymentMethod = "cash" | "card_pos" | "bank_transfer" | "other";

export type InvoiceLine = {
  id: string;
  inventory_part_id: string | null;
  item_type: InvoiceItemType;
  description: string;
  quantity: string;
  unit_price: string;
  line_total: string;
};

export type Payment = {
  id: string;
  amount: string;
  method: PaymentMethod;
  reference: string | null;
  notes: string | null;
  received_at: string;
};

export type Invoice = {
  id: string;
  work_order_id: string;
  invoice_number: string;
  status: InvoiceStatus;
  currency: string;
  subtotal: string;
  discount_amount: string;
  tax_rate: string;
  tax_amount: string;
  total_amount: string;
  paid_amount: string;
  balance_due: string;
  notes: string | null;
  issued_at: string;
  due_date: string | null;
  created_at: string;
  line_items: InvoiceLine[];
  payments: Payment[];
};

export type FinanceSummary = {
  invoiced_total: string;
  collected_total: string;
  outstanding_total: string;
  total_invoices: number;
  paid_invoices: number;
  partially_paid_invoices: number;
  overdue_invoices: number;
};

export type InvoiceCreatePayload = {
  line_items: Array<{
    item_type: InvoiceItemType;
    inventory_part_id: string | null;
    description: string;
    quantity: string;
    unit_price: string;
  }>;
  discount_amount: string;
  tax_rate: string;
  notes: string | null;
  due_date: string | null;
};

export type PaymentCreatePayload = {
  amount: string;
  method: PaymentMethod;
  reference: string | null;
  notes: string | null;
};

export type InventoryPart = {
  id: string;
  sku: string;
  name: string;
  brand: string | null;
  category: string | null;
  unit: string;
  stock_quantity: string;
  low_stock_threshold: string;
  purchase_price: string;
  sale_price: string;
  active: boolean;
  is_low_stock: boolean;
  created_at: string;
  updated_at: string;
};

export type StockMovementType = "initial" | "stock_in" | "stock_out" | "invoice_sale";

export type StockMovement = {
  id: string;
  part_id: string;
  movement_type: StockMovementType;
  quantity_delta: string;
  balance_after: string;
  reference_type: string | null;
  reference_id: string | null;
  notes: string | null;
  created_at: string;
};

export type InventorySummary = {
  total_parts: number;
  low_stock_parts: number;
  out_of_stock_parts: number;
  inventory_cost_value: string;
  inventory_sale_value: string;
};

