import type { WorkOrderStatus } from "./types";

export const STATUS_LABELS: Record<WorkOrderStatus, string> = {
  draft: "Taslak",
  inspection: "İncelemede",
  repairing: "Onarımda",
  waiting_parts: "Parça bekliyor",
  completed: "Tamamlandı",
  cancelled: "İptal",
};

export const STATUS_OPTIONS = Object.entries(STATUS_LABELS) as [WorkOrderStatus, string][];

export function formatDate(value: string) {
  return new Intl.DateTimeFormat("tr-TR", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function formatNumber(value: number | null | undefined) {
  return value == null ? "—" : new Intl.NumberFormat("tr-TR").format(value);
}

export function orderCode(id: string) {
  return `SE-${id.slice(0, 6).toUpperCase()}`;
}
