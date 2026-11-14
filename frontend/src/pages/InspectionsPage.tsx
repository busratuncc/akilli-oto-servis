import { useCallback, useEffect, useMemo, useState, type CSSProperties } from "react";
import {
  Activity,
  AlertTriangle,
  CarFront,
  CheckCircle2,
  ClipboardCheck,
  Gauge,
  Save,
  ShieldCheck,
  Wrench,
} from "lucide-react";
import { useSearchParams } from "react-router-dom";

import { api } from "../api";
import { useI18n } from "../i18n";
import type {
  InspectionCondition,
  InspectionItem,
  InspectionReport,
  InspectionStatus,
  Vehicle,
  WorkOrder,
} from "../types";
import { orderCode } from "../utils";

type Props = {
  vehicles: Vehicle[];
  orders: WorkOrder[];
  onChanged: () => Promise<void>;
  notify: (message: string) => void;
  reportError: (message: string) => void;
};

const conditionOptions: InspectionCondition[] = ["not_checked", "good", "attention", "critical"];
const categoryOrder = ["safety", "tires", "fluids", "electrical", "body"];

function cloneReport(report: InspectionReport): InspectionReport {
  return { ...report, items: report.items.map((item) => ({ ...item })) };
}

function calculateDraft(report: InspectionReport) {
  const checked = report.items.filter((item) => item.condition !== "not_checked");
  const weights: Record<InspectionCondition, number> = {
    not_checked: 0,
    good: 100,
    attention: 55,
    critical: 0,
  };
  return {
    healthScore: checked.length
      ? Math.round(checked.reduce((sum, item) => sum + weights[item.condition], 0) / checked.length)
      : 0,
    checkedCount: checked.length,
    attentionCount: report.items.filter((item) => item.condition === "attention").length,
    criticalCount: report.items.filter((item) => item.condition === "critical").length,
    unresolvedCriticalCount: report.items.filter((item) => item.condition === "critical" && !item.resolved).length,
  };
}

export function InspectionsPage({ vehicles, orders, onChanged, notify, reportError }: Props) {
  const { t } = useI18n();
  const [searchParams, setSearchParams] = useSearchParams();
  const [reports, setReports] = useState<InspectionReport[]>([]);
  const [selectedOrderId, setSelectedOrderId] = useState(searchParams.get("workOrder") ?? "");
  const [draft, setDraft] = useState<InspectionReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const loadReports = useCallback(async () => {
    try {
      setReports(await api.listInspections());
    } catch (error) {
      reportError(error instanceof Error ? error.message : t("inspection.loadError"));
    } finally {
      setLoading(false);
    }
  }, [reportError, t]);

  useEffect(() => { void loadReports(); }, [loadReports]);

  useEffect(() => {
    if (orders.length === 0) return;
    if (selectedOrderId && orders.some((order) => order.id === selectedOrderId)) return;
    const next = orders[0]?.id ?? "";
    setSelectedOrderId(next);
    if (next) setSearchParams({ workOrder: next }, { replace: true });
  }, [orders, selectedOrderId, setSearchParams]);

  const selectedOrder = orders.find((order) => order.id === selectedOrderId) ?? null;
  const selectedReport = reports.find((report) => report.work_order_id === selectedOrderId) ?? null;
  const vehicleMap = useMemo(() => new Map(vehicles.map((vehicle) => [vehicle.id, vehicle])), [vehicles]);
  const reportMap = useMemo(() => new Map(reports.map((report) => [report.work_order_id, report])), [reports]);

  useEffect(() => {
    setDraft(selectedReport ? cloneReport(selectedReport) : null);
  }, [selectedReport]);

  const metrics = draft ? calculateDraft(draft) : null;
  const groupedItems = useMemo(() => {
    if (!draft) return [];
    return categoryOrder.map((category) => ({
      category,
      items: draft.items.filter((item) => item.category === category),
    })).filter((group) => group.items.length > 0);
  }, [draft]);

  function chooseOrder(id: string) {
    setSelectedOrderId(id);
    setSearchParams({ workOrder: id }, { replace: true });
  }

  async function startInspection() {
    if (!selectedOrder) return;
    setSaving(true);
    try {
      const created = await api.createInspection(selectedOrder.id);
      setReports((current) => [created, ...current]);
      setDraft(cloneReport(created));
      notify(t("inspection.created"));
    } catch (error) {
      reportError(error instanceof Error ? error.message : t("inspection.createError"));
    } finally {
      setSaving(false);
    }
  }

  function updateItem(itemKey: string, changes: Partial<InspectionItem>) {
    setDraft((current) => current ? {
      ...current,
      items: current.items.map((item) => item.item_key === itemKey ? { ...item, ...changes } : item),
    } : current);
  }

  async function saveInspection(status?: InspectionStatus) {
    if (!draft) return;
    const currentMetrics = calculateDraft(draft);
    if (status === "completed") {
      if (currentMetrics.checkedCount !== draft.items.length) {
        reportError(t("inspection.completeAllError"));
        return;
      }
      if (currentMetrics.unresolvedCriticalCount > 0) {
        reportError(t("inspection.resolveCriticalError"));
        return;
      }
      if (!draft.mechanic_approved) {
        reportError(t("inspection.approvalError"));
        return;
      }
    }
    setSaving(true);
    try {
      const updated = await api.updateInspection(draft.id, {
        ...(status ? { status } : {}),
        odometer: draft.odometer,
        technician_name: draft.technician_name?.trim() || null,
        notes: draft.notes?.trim() || null,
        mechanic_approved: draft.mechanic_approved,
        items: draft.items.map((item) => ({
          item_key: item.item_key,
          condition: item.condition,
          measurement: item.measurement?.trim() || null,
          notes: item.notes?.trim() || null,
          resolved: item.resolved,
        })),
      });
      setReports((current) => current.map((report) => report.id === updated.id ? updated : report));
      setDraft(cloneReport(updated));
      notify(t(status === "completed" ? "inspection.completed" : "inspection.saved"));
      await onChanged();
    } catch (error) {
      reportError(error instanceof Error ? error.message : t("inspection.saveError"));
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <div className="loading-card">{t("inspection.loading")}</div>;

  return (
    <div className="page-stack inspection-page">
      <div className="page-title-row">
        <div><span className="section-kicker">{t("inspection.kicker")}</span><h2>{t("inspection.title")}</h2><p>{t("inspection.subtitle")}</p></div>
      </div>

      <section className="inspection-layout">
        <aside className="panel inspection-order-panel">
          <div className="panel-heading"><div><span className="section-kicker">{t("inspection.workOrders", { count: orders.length })}</span><h3>{t("inspection.selectOrder")}</h3></div></div>
          <div className="inspection-order-list">
            {orders.map((order) => {
              const vehicle = vehicleMap.get(order.vehicle_id);
              const report = reportMap.get(order.id);
              return <button className={`inspection-order-row ${order.id === selectedOrderId ? "selected" : ""}`} key={order.id} onClick={() => chooseOrder(order.id)}>
                <span className="order-row-icon"><Wrench size={17} /></span><span><strong>{vehicle ? `${vehicle.brand} ${vehicle.model}` : t("common.unknownVehicle")}</strong><small>{orderCode(order.id)} · {vehicle?.anonymous_code}</small></span>{report ? <i className={`inspection-state inspection-state-${report.status}`}>{t(`inspection.status.${report.status}`)}</i> : <i className="inspection-state">{t("inspection.notStarted")}</i>}
              </button>;
            })}
            {orders.length === 0 && <div className="empty-state"><ClipboardCheck size={30} /><p>{t("inspection.noOrders")}</p></div>}
          </div>
        </aside>

        <main className="inspection-workspace">
          {!selectedOrder ? <div className="panel empty-state inspection-empty"><ClipboardCheck size={38} /><p>{t("inspection.selectHelp")}</p></div> : !draft ? <div className="panel inspection-start-card"><span className="inspection-start-icon"><ClipboardCheck size={30} /></span><span className="section-kicker">{orderCode(selectedOrder.id)}</span><h3>{t("inspection.startTitle")}</h3><p>{t("inspection.startHelp")}</p><div className="quality-note"><ShieldCheck size={18} /> {t("inspection.qualityNote")}</div><button className="primary-button" disabled={saving} onClick={() => void startInspection()}><ClipboardCheck size={17} /> {t("inspection.start")}</button></div> : <>
            <section className="panel inspection-summary-panel">
              <div className="inspection-report-head"><div><span className="section-kicker">{orderCode(selectedOrder.id)}</span><h3>{t("inspection.reportTitle")}</h3></div><span className={`inspection-report-status report-status-${draft.status}`}>{t(`inspection.status.${draft.status}`)}</span></div>
              <div className="inspection-metrics">
                <div className="health-score"><span style={{ "--score": `${metrics?.healthScore ?? 0}%` } as CSSProperties}><strong>{metrics?.healthScore ?? 0}</strong><small>/100</small></span><p>{t("inspection.healthScore")}</p></div>
                <div><span className="metric-icon blue"><ClipboardCheck size={20} /></span><strong>{metrics?.checkedCount}/{draft.items.length}</strong><small>{t("inspection.checked")}</small></div>
                <div><span className="metric-icon orange"><Activity size={20} /></span><strong>{metrics?.attentionCount}</strong><small>{t("inspection.attention")}</small></div>
                <div><span className="metric-icon purple"><AlertTriangle size={20} /></span><strong>{metrics?.criticalCount}</strong><small>{t("inspection.critical")}</small></div>
              </div>
              <div className="inspection-meta-form">
                <label>{t("inspection.technician")}<input value={draft.technician_name ?? ""} onChange={(event) => setDraft({ ...draft, technician_name: event.target.value })} placeholder={t("inspection.technicianPlaceholder")} /></label>
                <label>{t("inspection.odometer")}<input type="number" min="0" max="5000000" value={draft.odometer ?? ""} onChange={(event) => setDraft({ ...draft, odometer: event.target.value ? Number(event.target.value) : null })} /></label>
                <label>{t("inspection.generalNotes")}<input value={draft.notes ?? ""} onChange={(event) => setDraft({ ...draft, notes: event.target.value })} placeholder={t("inspection.notesPlaceholder")} /></label>
              </div>
            </section>

            {groupedItems.map(({ category, items }) => <section className="panel inspection-category" key={category}>
              <div className="inspection-category-head"><span className={`category-icon category-${category}`}>{category === "safety" ? <ShieldCheck size={19} /> : category === "tires" ? <Gauge size={19} /> : category === "electrical" ? <Activity size={19} /> : <CarFront size={19} />}</span><div><span className="section-kicker">{t(`inspection.category.${category}`)}</span><h3>{t(`inspection.categoryHelp.${category}`)}</h3></div></div>
              <div className="inspection-item-list">{items.map((item) => <article className={`inspection-item item-${item.condition}`} key={item.id}>
                <div className="inspection-item-title"><strong>{t(`inspection.item.${item.item_key}`)}</strong><span>{item.position.toString().padStart(2, "0")}</span></div>
                <div className="condition-toggle">{conditionOptions.map((condition) => <button type="button" className={item.condition === condition ? `active condition-${condition}` : ""} key={condition} onClick={() => updateItem(item.item_key, { condition, resolved: condition === "critical" ? item.resolved : false })}>{condition === "good" && <CheckCircle2 size={14} />}{condition === "attention" && <Activity size={14} />}{condition === "critical" && <AlertTriangle size={14} />}{t(`inspection.condition.${condition}`)}</button>)}</div>
                <input className="inspection-measurement" value={item.measurement ?? ""} onChange={(event) => updateItem(item.item_key, { measurement: event.target.value })} placeholder={t("inspection.measurement")} />
                <input className="inspection-item-note" value={item.notes ?? ""} onChange={(event) => updateItem(item.item_key, { notes: event.target.value })} placeholder={t("inspection.itemNote")} />
                {item.condition === "critical" && <label className="critical-resolved"><input type="checkbox" checked={item.resolved} onChange={(event) => updateItem(item.item_key, { resolved: event.target.checked })} /><span>{t("inspection.criticalResolved")}</span></label>}
              </article>)}</div>
            </section>)}

            <section className="panel inspection-completion">
              <label className="check-label"><input type="checkbox" checked={draft.mechanic_approved} onChange={(event) => setDraft({ ...draft, mechanic_approved: event.target.checked })} /><span><strong>{t("inspection.mechanicApproval")}</strong><small>{t("inspection.mechanicApprovalHelp")}</small></span></label>
              {metrics && metrics.unresolvedCriticalCount > 0 && <div className="inline-warning"><AlertTriangle size={17} /> {t("inspection.unresolvedWarning", { count: metrics.unresolvedCriticalCount })}</div>}
              <div className="inspection-actions"><button className="ghost-button" disabled={saving} onClick={() => selectedReport && setDraft(cloneReport(selectedReport))}>{t("inspection.undo")}</button><button className="secondary-button" disabled={saving} onClick={() => void saveInspection()}><Save size={16} /> {saving ? t("common.saving") : t("inspection.saveDraft")}</button><button className="primary-button" disabled={saving || draft.status === "completed"} onClick={() => void saveInspection("completed")}><ShieldCheck size={16} /> {t("inspection.complete")}</button></div>
            </section>
          </>}
        </main>
      </section>
    </div>
  );
}
