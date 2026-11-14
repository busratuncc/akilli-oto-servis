import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import {
  BarChart3,
  CheckCircle2,
  Clock3,
  Database,
  FlaskConical,
  Play,
  Plus,
  Target,
  Trash2,
} from "lucide-react";

import { api } from "../api";
import { useI18n } from "../i18n";
import type {
  EvaluationMode,
  EvaluationQuery,
  EvaluationRun,
  EvaluationSummary,
  Vehicle,
  WorkOrder,
} from "../types";
import { formatDate, orderCode } from "../utils";

type Props = {
  vehicles: Vehicle[];
  orders: WorkOrder[];
  notify: (message: string) => void;
  reportError: (message: string) => void;
};

const emptyForm = {
  name: "",
  query_text: "",
  dtc_code: "",
  expected_work_order_id: "",
  notes: "",
};

const ALL_MODES: EvaluationMode[] = ["keyword", "semantic", "hybrid"];

export function EvaluationPage({ vehicles, orders, notify, reportError }: Props) {
  const { language, t } = useI18n();
  const [queries, setQueries] = useState<EvaluationQuery[]>([]);
  const [runs, setRuns] = useState<EvaluationRun[]>([]);
  const [summary, setSummary] = useState<EvaluationSummary | null>(null);
  const [form, setForm] = useState(emptyForm);
  const [modes, setModes] = useState<EvaluationMode[]>(ALL_MODES);
  const [topK, setTopK] = useState(5);
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [running, setRunning] = useState(false);
  const [loading, setLoading] = useState(true);

  const loadEvaluation = useCallback(async () => {
    try {
      const [queryData, runData, summaryData] = await Promise.all([
        api.listEvaluationQueries(),
        api.listEvaluationRuns(),
        api.evaluationSummary(),
      ]);
      setQueries(queryData);
      setRuns(runData);
      setSummary(summaryData);
    } catch (error) {
      reportError(error instanceof Error ? error.message : t("evaluation.loadError"));
    } finally {
      setLoading(false);
    }
  }, [reportError, t]);

  useEffect(() => {
    void loadEvaluation();
  }, [loadEvaluation]);

  const approvedOrders = orders.filter((order) => order.approved_by_mechanic);
  const vehicleMap = useMemo(
    () => new Map(vehicles.map((vehicle) => [vehicle.id, vehicle])),
    [vehicles],
  );
  const orderMap = useMemo(() => new Map(orders.map((order) => [order.id, order])), [orders]);
  const latestRun = runs[0] ?? null;

  function selectExpectedOrder(orderId: string) {
    const order = orderMap.get(orderId);
    const dtc = order?.dtc_codes[0]?.code ?? "";
    setForm((current) => ({
      ...current,
      expected_work_order_id: orderId,
      name: order ? `${orderCode(order.id)} · ${order.customer_complaint.slice(0, 60)}` : "",
      query_text: "",
      dtc_code: dtc,
    }));
  }

  function toggleMode(mode: EvaluationMode) {
    setModes((current) => current.includes(mode)
      ? current.filter((item) => item !== mode)
      : [...current, mode]);
  }

  async function createQuery(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    try {
      await api.createEvaluationQuery({
        name: form.name,
        query_text: form.query_text,
        dtc_code: form.dtc_code.trim() || null,
        expected_work_order_id: form.expected_work_order_id,
        notes: form.notes.trim() || null,
      });
      setForm(emptyForm);
      setShowForm(false);
      notify(t("evaluation.queryCreated"));
      await loadEvaluation();
    } catch (error) {
      reportError(error instanceof Error ? error.message : t("evaluation.queryError"));
    } finally {
      setSaving(false);
    }
  }

  async function deleteQuery(item: EvaluationQuery) {
    if (!window.confirm(t("evaluation.deleteConfirm"))) return;
    try {
      await api.deleteEvaluationQuery(item.id);
      notify(t("evaluation.queryDeleted"));
      await loadEvaluation();
    } catch (error) {
      reportError(error instanceof Error ? error.message : t("evaluation.deleteError"));
    }
  }

  async function runExperiment() {
    if (!modes.length) {
      reportError(t("evaluation.modeRequired"));
      return;
    }
    setRunning(true);
    try {
      const result = await api.runEvaluation(modes, topK);
      notify(t("evaluation.runCompleted", { mode: t(`evaluation.mode.${result.best_mode ?? modes[0]}`) }));
      await loadEvaluation();
    } catch (error) {
      reportError(error instanceof Error ? error.message : t("evaluation.runError"));
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="page-stack">
      <section className="page-title-row">
        <div><span className="section-kicker">{t("evaluation.kicker")}</span><h2>{t("evaluation.title")}</h2><p>{t("evaluation.subtitle")}</p></div>
        <button className="primary-button" onClick={() => setShowForm((value) => !value)}><Plus size={18} /> {t("evaluation.addQuery")}</button>
      </section>

      <section className="metric-grid evaluation-metrics">
        <div className="metric-card"><span className="metric-icon blue"><Database size={22} /></span><div><strong>{summary?.query_count ?? 0}</strong><span>{t("evaluation.datasetSize")}</span></div></div>
        <div className="metric-card"><span className="metric-icon purple"><FlaskConical size={22} /></span><div><strong>{summary?.run_count ?? 0}</strong><span>{t("evaluation.runCount")}</span></div></div>
        <div className="metric-card"><span className="metric-icon green"><Target size={22} /></span><div><strong>%{Math.round((summary?.best_hit_rate ?? 0) * 100)}</strong><span>{t("evaluation.bestHit")}</span></div></div>
        <div className="metric-card"><span className="metric-icon orange"><BarChart3 size={22} /></span><div><strong>{summary?.best_mode ? t(`evaluation.mode.${summary.best_mode}`) : "—"}</strong><span>{t("evaluation.bestMode")}</span></div></div>
      </section>

      <div className="evaluation-research-note"><FlaskConical size={20} /><span><strong>{t("evaluation.researchTitle")}</strong>{t("evaluation.researchNote")}</span></div>

      {showForm && <section className="panel form-panel"><div className="panel-heading"><div><span className="section-kicker">{t("evaluation.dataset")}</span><h3>{t("evaluation.newQuery")}</h3></div></div>{approvedOrders.length === 0 ? <div className="inline-warning">{t("evaluation.needApproved")}</div> : <form className="evaluation-query-form" onSubmit={createQuery}>
        <label className="span-2">{t("evaluation.expectedCase")}<select required value={form.expected_work_order_id} onChange={(event) => selectExpectedOrder(event.target.value)}><option value="">{t("common.select")}</option>{approvedOrders.map((order) => { const vehicle = vehicleMap.get(order.vehicle_id); return <option key={order.id} value={order.id}>{orderCode(order.id)} · {vehicle?.brand} {vehicle?.model} · {order.customer_complaint}</option>; })}</select></label>
        <label>{t("evaluation.queryName")}<input required minLength={2} value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} /></label>
        <label>{t("evaluation.dtc")}<input value={form.dtc_code} maxLength={5} onChange={(event) => setForm({ ...form, dtc_code: event.target.value.toUpperCase() })} placeholder="P0299" /></label>
        <div className="inline-warning span-2">{t("evaluation.leakWarning")}</div>
        <label className="span-2">{t("evaluation.queryText")}<textarea required minLength={3} rows={3} value={form.query_text} onChange={(event) => setForm({ ...form, query_text: event.target.value })} placeholder={t("evaluation.queryPlaceholder")} /></label>
        <label className="span-2">{t("evaluation.notes")}<textarea rows={2} value={form.notes} onChange={(event) => setForm({ ...form, notes: event.target.value })} /></label>
        <div className="form-actions span-2"><button type="button" className="ghost-button" onClick={() => setShowForm(false)}>{t("common.cancel")}</button><button className="primary-button" disabled={saving}>{saving ? t("common.saving") : t("evaluation.saveQuery")}</button></div>
      </form>}</section>}

      <section className="evaluation-layout">
        <article className="panel experiment-panel">
          <div className="panel-heading"><div><span className="section-kicker">{t("evaluation.experiment")}</span><h3>{t("evaluation.compareMethods")}</h3></div></div>
          <div className="experiment-controls"><div className="mode-checks">{ALL_MODES.map((mode) => <label className="check-label" key={mode}><input type="checkbox" checked={modes.includes(mode)} onChange={() => toggleMode(mode)} /><span>{t(`evaluation.mode.${mode}`)}<small>{t(`evaluation.modeHelp.${mode}`)}</small></span></label>)}</div><label>{t("evaluation.topK")}<select value={topK} onChange={(event) => setTopK(Number(event.target.value))}>{[1, 3, 5, 10].map((value) => <option key={value} value={value}>Top {value}</option>)}</select></label><button className="primary-button" disabled={running || queries.length === 0} onClick={() => void runExperiment()}><Play size={17} /> {running ? t("evaluation.running") : t("evaluation.run")}</button></div>

          {latestRun ? <><div className="evaluation-run-meta"><span><Clock3 size={15} /> {formatDate(latestRun.created_at, language)}</span><span>Top {latestRun.top_k}</span><span>{latestRun.query_count} {t("evaluation.queriesShort")}</span></div><div className="metrics-table"><div className="metrics-row head"><span>{t("evaluation.method")}</span><span>Hit@{latestRun.top_k}</span><span>MRR</span><span>{t("evaluation.latency")}</span></div>{latestRun.metrics.map((metric) => <div className={`metrics-row ${latestRun.best_mode === metric.mode ? "best" : ""}`} key={metric.mode}><strong>{t(`evaluation.mode.${metric.mode}`)}</strong><span><b>%{Math.round(metric.hit_rate * 100)}</b><i style={{ width: `${metric.hit_rate * 100}%` }} /></span><span>{metric.mrr.toFixed(3)}</span><span>{metric.avg_latency_ms.toFixed(1)} ms</span></div>)}</div></> : <div className="empty-state"><BarChart3 size={30} /><p>{t("evaluation.noRun")}</p><small>{t("evaluation.noRunHelp")}</small></div>}
        </article>

        <aside className="panel evaluation-dataset-panel"><div className="panel-heading"><div><span className="section-kicker">{t("evaluation.dataset")}</span><h3>{t("evaluation.queries")}</h3></div><span className="code-chip">{queries.length}</span></div>{loading ? <div className="empty-state"><p>{t("evaluation.loading")}</p></div> : <div className="evaluation-query-list">{queries.map((item) => { const order = orderMap.get(item.expected_work_order_id); const vehicle = order ? vehicleMap.get(order.vehicle_id) : null; return <div key={item.id}><span className="query-target"><Target size={17} /></span><span><strong>{item.name}</strong><small>{vehicle ? `${vehicle.brand} ${vehicle.model} · ` : ""}{orderCode(item.expected_work_order_id)}{item.dtc_code ? ` · ${item.dtc_code}` : ""}</small><p>{item.query_text}</p></span><button onClick={() => void deleteQuery(item)} title={t("evaluation.delete")}><Trash2 size={16} /></button></div>; })}{queries.length === 0 && <div className="empty-state"><Database size={30} /><p>{t("evaluation.noQueries")}</p><small>{t("evaluation.noQueriesHelp")}</small></div>}</div>}</aside>
      </section>

      {latestRun && <section className="panel"><div className="panel-heading"><div><span className="section-kicker">{t("evaluation.details")}</span><h3>{t("evaluation.latestResults")}</h3></div></div><div className="evaluation-detail-table"><div className="evaluation-detail-row head"><span>{t("evaluation.query")}</span><span>{t("evaluation.method")}</span><span>{t("evaluation.rank")}</span><span>{t("evaluation.latency")}</span></div>{latestRun.details.slice(0, 30).map((detail) => <div className="evaluation-detail-row" key={`${detail.query_id}-${detail.mode}`}><strong>{detail.query_name}</strong><span>{t(`evaluation.mode.${detail.mode}`)}</span><span>{detail.rank ? <b className="rank-hit"><CheckCircle2 size={14} /> #{detail.rank}</b> : <b className="rank-miss">—</b>}</span><span>{detail.latency_ms.toFixed(1)} ms</span></div>)}</div></section>}
    </div>
  );
}
