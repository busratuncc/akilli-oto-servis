import type { WorkOrderStatus } from "../types";
import { useI18n } from "../i18n";

export function StatusBadge({ status }: { status: WorkOrderStatus }) {
  const { t } = useI18n();
  return <span className={`status-badge status-${status}`}>{t(`status.${status}`)}</span>;
}
