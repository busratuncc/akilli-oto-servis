import type { WorkOrderStatus } from "./types";

export const WORK_ORDER_STATUSES: WorkOrderStatus[] = [
  "draft",
  "inspection",
  "repairing",
  "waiting_parts",
  "completed",
  "cancelled",
];

export function formatDate(value: string, language: "tr" | "en" = "tr") {
  return new Intl.DateTimeFormat(language === "tr" ? "tr-TR" : "en-GB", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function formatNumber(value: number | null | undefined, language: "tr" | "en" = "tr") {
  return value == null ? "—" : new Intl.NumberFormat(language === "tr" ? "tr-TR" : "en-GB").format(value);
}

export function orderCode(id: string) {
  return `SE-${id.slice(0, 6).toUpperCase()}`;
}
