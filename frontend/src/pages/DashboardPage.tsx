import { CarFront, CheckCircle2, ClipboardList, Clock3, ShieldCheck } from "lucide-react";
import { Link } from "react-router-dom";

import { StatusBadge } from "../components/StatusBadge";
import type { DashboardSummary, Vehicle } from "../types";
import { formatDate, orderCode, STATUS_LABELS } from "../utils";

type Props = {
  summary: DashboardSummary | null;
  vehicleMap: Map<string, Vehicle>;
};

export function DashboardPage({ summary, vehicleMap }: Props) {
  if (!summary) {
    return <div className="loading-card">Gösterge paneli hazırlanıyor…</div>;
  }

  const cards = [
    { label: "Kayıtlı araç", value: summary.total_vehicles, icon: CarFront, tone: "blue" },
    { label: "Açık iş emri", value: summary.open_work_orders, icon: Clock3, tone: "orange" },
    { label: "Tamamlanan", value: summary.completed_work_orders, icon: CheckCircle2, tone: "green" },
    { label: "Usta onaylı vaka", value: summary.approved_cases, icon: ShieldCheck, tone: "purple" },
  ];

  return (
    <div className="page-stack">
      <section className="welcome-panel">
        <div>
          <span className="section-kicker">Günün özeti</span>
          <h2>Atölyedeki tüm işler tek ekranda</h2>
          <p>Araç kabulünden tamamlanan onarıma kadar servis sürecini takip edin.</p>
        </div>
        <Link to="/work-orders" className="primary-link"><ClipboardList size={18} /> Yeni iş emri</Link>
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
            <div><span className="section-kicker">Canlı durum</span><h3>İş emri dağılımı</h3></div>
          </div>
          <div className="status-overview">
            {Object.entries(STATUS_LABELS).map(([status, label]) => {
              const count = summary.status_counts[status as keyof typeof summary.status_counts] ?? 0;
              const percent = summary.total_work_orders ? Math.round((count / summary.total_work_orders) * 100) : 0;
              return (
                <div className="status-row" key={status}>
                  <div><span>{label}</span><strong>{count}</strong></div>
                  <div className="progress-track"><span style={{ width: `${percent}%` }} /></div>
                </div>
              );
            })}
          </div>
        </article>

        <article className="panel recent-panel">
          <div className="panel-heading">
            <div><span className="section-kicker">Son hareketler</span><h3>Güncel servis kayıtları</h3></div>
            <Link to="/work-orders">Tümünü gör</Link>
          </div>
          <div className="compact-list">
            {summary.recent_work_orders.map((order) => {
              const vehicle = vehicleMap.get(order.vehicle_id);
              return (
                <div className="compact-row" key={order.id}>
                  <div className="row-avatar"><CarFront size={18} /></div>
                  <div className="row-main">
                    <strong>{vehicle ? `${vehicle.brand} ${vehicle.model}` : "Bilinmeyen araç"}</strong>
                    <span>{orderCode(order.id)} · {formatDate(order.created_at)}</span>
                  </div>
                  <StatusBadge status={order.status} />
                </div>
              );
            })}
            {summary.recent_work_orders.length === 0 && (
              <div className="empty-state"><ClipboardList size={28} /><p>Henüz iş emri yok.</p></div>
            )}
          </div>
        </article>
      </section>
    </div>
  );
}
