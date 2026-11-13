import type { WorkOrderStatus } from "../types";
import { STATUS_LABELS } from "../utils";

export function StatusBadge({ status }: { status: WorkOrderStatus }) {
  return <span className={`status-badge status-${status}`}>{STATUS_LABELS[status]}</span>;
}
