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

