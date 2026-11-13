import { CarFront, CheckCircle2, ClipboardList, Clock3, ShieldCheck } from "lucide-react";
import { Link } from "react-router-dom";

import { StatusBadge } from "../components/StatusBadge";
import { useI18n } from "../i18n";
import type { DashboardSummary, Vehicle } from "../types";
import { formatDate, orderCode, WORK_ORDER_STATUSES } from "../utils";

type Props = {
  summary: DashboardSummary | null;
  vehicleMap: Map<string, Vehicle>;
};

export function DashboardPage({ summary, vehicleMap }: Props) {
  const { language, t } = useI18n();
  if (!summary) {
    return <div className="loading-card">{t("dashboard.loading")}</div>;
  }

  const cards = [
    { label: t("dashboard.registeredVehicles"), value: summary.total_vehicles, icon: CarFront, tone: "blue" },
    { label: t("dashboard.openOrders"), value: summary.open_work_orders, icon: Clock3, tone: "orange" },
    { label: t("dashboard.completed"), value: summary.completed_work_orders, icon: CheckCircle2, tone: "green" },
    { label: t("dashboard.approved"), value: summary.approved_cases, icon: ShieldCheck, tone: "purple" },
  ];

  return (
    <div className="page-stack">
      <section className="welcome-panel">
        <div>
          <span className="section-kicker">{t("dashboard.kicker")}</span>
          <h2>{t("dashboard.title")}</h2>
          <p>{t("dashboard.subtitle")}</p>
        </div>
        <Link to="/work-orders" className="primary-link"><ClipboardList size={18} /> {t("dashboard.newOrder")}</Link>
      </section>

      <section className="metric-grid">
        {cards.map(({ label, value, icon: Icon, tone }) => (
          <article className="metric-card" key={label}>
            <span className={`metric-icon ${tone}`}><Icon size={21} /></span>
            <div><strong>{value}</strong><span>{label}</span></div>
          </article>
        ))}
      </section>

      <section className="dashboard-grid">
        <article className="panel">
          <div className="panel-heading">
            <div><span className="section-kicker">{t("dashboard.live")}</span><h3>{t("dashboard.distribution")}</h3></div>
          </div>
          <div className="status-overview">
            {WORK_ORDER_STATUSES.map((status) => {
              const count = summary.status_counts[status] ?? 0;
              const percent = summary.total_work_orders ? Math.round((count / summary.total_work_orders) * 100) : 0;
              return (
                <div className="status-row" key={status}>
                  <div><span>{t(`status.${status}`)}</span><strong>{count}</strong></div>
                  <div className="progress-track"><span style={{ width: `${percent}%` }} /></div>
                </div>
              );
            })}
          </div>
        </article>

        <article className="panel recent-panel">
          <div className="panel-heading">
            <div><span className="section-kicker">{t("dashboard.recent")}</span><h3>{t("dashboard.currentRecords")}</h3></div>
            <Link to="/work-orders">{t("dashboard.viewAll")}</Link>
          </div>
          <div className="compact-list">
            {summary.recent_work_orders.map((order) => {
              const vehicle = vehicleMap.get(order.vehicle_id);
              return (
                <div className="compact-row" key={order.id}>
                  <div className="row-avatar"><CarFront size={18} /></div>
                  <div className="row-main">
                    <strong>{vehicle ? `${vehicle.brand} ${vehicle.model}` : t("common.unknownVehicle")}</strong>
                    <span>{orderCode(order.id)} · {formatDate(order.created_at, language)}</span>
                  </div>
                  <StatusBadge status={order.status} />
                </div>
              );
            })}
            {summary.recent_work_orders.length === 0 && (
              <div className="empty-state"><ClipboardList size={28} /><p>{t("dashboard.noOrders")}</p></div>
            )}
          </div>
        </article>
      </section>
    </div>
  );
}
