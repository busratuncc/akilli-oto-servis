import {
  AlertTriangle,
  Banknote,
  Boxes,
  CheckCircle2,
  ClipboardCheck,
  ClipboardList,
  Clock3,
  FileCheck2,
  HeartPulse,
  ReceiptText,
  TrendingDown,
  TrendingUp,
  UsersRound,
  Wrench,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { api } from "../api";
import { useI18n } from "../i18n";
import type { AnalyticsMetric, AnalyticsOverview, AnalyticsSeriesPoint } from "../types";
import { formatCurrency, formatNumber } from "../utils";

type Props = { reportError: (message: string) => void };
type Period = 7 | 30 | 90;

const PERIODS: Period[] = [7, 30, 90];

function shortDate(value: string, language: "tr" | "en") {
  return new Intl.DateTimeFormat(language === "tr" ? "tr-TR" : "en-GB", {
    day: "2-digit",
    month: "short",
  }).format(new Date(`${value}T00:00:00`));
}

function periodDate(value: string, language: "tr" | "en") {
  return new Intl.DateTimeFormat(language === "tr" ? "tr-TR" : "en-GB", {
    dateStyle: "medium",
    timeZone: "Europe/Istanbul",
  }).format(new Date(value));
}

function compactMoney(value: number, language: "tr" | "en") {
  return new Intl.NumberFormat(language === "tr" ? "tr-TR" : "en-GB", {
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(value);
}

function RevenueChart({ rows }: { rows: AnalyticsSeriesPoint[] }) {
  const { language, t } = useI18n();
  const width = 760;
  const height = 245;
  const left = 58;
  const right = 18;
  const top = 18;
  const bottom = 40;
  const plotWidth = width - left - right;
  const plotHeight = height - top - bottom;
  const maxValue = Math.max(1, ...rows.flatMap((row) => [Number(row.invoiced), Number(row.collected)]));
  const point = (value: number, index: number) => {
    const x = left + (rows.length <= 1 ? plotWidth / 2 : (index / (rows.length - 1)) * plotWidth);
    const y = top + plotHeight - (value / maxValue) * plotHeight;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  };
  const labelIndexes = Array.from(new Set([0, Math.floor((rows.length - 1) / 2), rows.length - 1]));

  return (
    <div className="analytics-chart-wrap">
      <div className="analytics-legend" aria-label="legend">
        <span><i className="legend-line invoiced" />{t("analytics.invoicedLegend")}</span>
        <span><i className="legend-line collected" />{t("analytics.collectedLegend")}</span>
      </div>
      <svg className="revenue-chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={t("analytics.revenueTrend")}>
        {[0, 0.5, 1].map((ratio) => {
          const y = top + plotHeight * ratio;
          const value = maxValue * (1 - ratio);
          return <g key={ratio}><line x1={left} x2={width - right} y1={y} y2={y} className="chart-grid-line" /><text x={left - 10} y={y + 4} textAnchor="end" className="chart-axis-label">{compactMoney(value, language)}</text></g>;
        })}
        <polyline points={rows.map((row, index) => point(Number(row.invoiced), index)).join(" ")} className="chart-line invoiced" />
        <polyline points={rows.map((row, index) => point(Number(row.collected), index)).join(" ")} className="chart-line collected" />
        {rows.length <= 30 && rows.map((row, index) => {
          const [invoiceX, invoiceY] = point(Number(row.invoiced), index).split(",");
          const [paymentX, paymentY] = point(Number(row.collected), index).split(",");
          return <g key={row.day}>
            <circle cx={invoiceX} cy={invoiceY} r="3.2" className="chart-dot invoiced"><title>{shortDate(row.day, language)} · {t("analytics.invoicedLegend")}: {formatCurrency(row.invoiced, language)}</title></circle>
            <circle cx={paymentX} cy={paymentY} r="3.2" className="chart-dot collected"><title>{shortDate(row.day, language)} · {t("analytics.collectedLegend")}: {formatCurrency(row.collected, language)}</title></circle>
          </g>;
        })}
        {labelIndexes.map((index) => rows[index] && <text key={rows[index].day} x={left + (rows.length <= 1 ? plotWidth / 2 : (index / (rows.length - 1)) * plotWidth)} y={height - 12} textAnchor={index === 0 ? "start" : index === rows.length - 1 ? "end" : "middle"} className="chart-axis-label">{shortDate(rows[index].day, language)}</text>)}
      </svg>
    </div>
  );
}

function CompletedChart({ rows }: { rows: AnalyticsSeriesPoint[] }) {
  const { language, t } = useI18n();
  const max = Math.max(1, ...rows.map((row) => row.completed_orders));
  return (
    <div className="completion-chart" role="img" aria-label={t("analytics.completedTrend")}>
      {rows.map((row) => (
        <span key={row.day} className="completion-column" title={`${shortDate(row.day, language)}: ${row.completed_orders}`}>
          <i style={{ height: `${Math.max(row.completed_orders ? 8 : 2, (row.completed_orders / max) * 100)}%` }} className={row.completed_orders ? "has-value" : ""} />
        </span>
      ))}
    </div>
  );
}

function Delta({ metric, goodWhenUp }: { metric: AnalyticsMetric; goodWhenUp: boolean }) {
  const { t } = useI18n();
  if (metric.current == null) return <small className="analytics-delta neutral">{t("analytics.noData")}</small>;
  if (metric.change_percent == null) return <small className="analytics-delta neutral">{t("analytics.newPeriod")}</small>;
  if (metric.change_percent === 0) return <small className="analytics-delta neutral">{t("analytics.noChange")}</small>;
  const isUp = metric.change_percent > 0;
  const favorable = isUp === goodWhenUp;
  const Icon = isUp ? TrendingUp : TrendingDown;
  return <small className={`analytics-delta ${favorable ? "good" : "bad"}`}><Icon size={13} /> %{Math.abs(metric.change_percent)} {t("analytics.vsPrevious")}</small>;
}

export function AnalyticsPage({ reportError }: Props) {
  const { language, t } = useI18n();
  const [period, setPeriod] = useState<Period>(30);
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    setLoading(true);
    void api.analyticsOverview(period)
      .then((result) => { if (active) setOverview(result); })
      .catch(() => { if (active) reportError(t("analytics.loadError")); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [period, reportError, t]);

  const totalOrders = useMemo(() => overview?.work_order_statuses.reduce((sum, item) => sum + item.count, 0) ?? 0, [overview]);
  const maxFunnel = Math.max(1, ...(overview?.estimate_funnel.map((item) => item.count) ?? [0]));
  const maxService = Math.max(1, ...(overview?.top_services.map((item) => item.count) ?? [0]));

  if (!overview && loading) return <div className="loading-card">{t("analytics.loading")}</div>;
  if (!overview) return <div className="loading-card">{t("analytics.loadError")}</div>;

  const kpis = [
    { key: "invoiced", label: t("analytics.invoiced"), metric: overview.invoiced, icon: ReceiptText, tone: "blue", format: (value: number) => formatCurrency(value, language), goodWhenUp: true },
    { key: "collected", label: t("analytics.collected"), metric: overview.collected, icon: Banknote, tone: "green", format: (value: number) => formatCurrency(value, language), goodWhenUp: true },
    { key: "completed", label: t("analytics.completedOrders"), metric: overview.completed_orders, icon: CheckCircle2, tone: "purple", format: (value: number) => formatNumber(value, language), goodWhenUp: true },
    { key: "turnaround", label: t("analytics.turnaround"), metric: overview.average_turnaround_hours, icon: Clock3, tone: "orange", format: (value: number) => t("analytics.hours", { value: formatNumber(value, language) }), goodWhenUp: false },
    { key: "approval", label: t("analytics.approvalRate"), metric: overview.estimate_approval_rate, icon: FileCheck2, tone: "green", format: (value: number) => `%${formatNumber(value, language)}`, goodWhenUp: true },
    { key: "no-show", label: t("analytics.noShowRate"), metric: overview.appointment_no_show_rate, icon: UsersRound, tone: "orange", format: (value: number) => `%${formatNumber(value, language)}`, goodWhenUp: false },
  ];
  const snapshots = [
    { label: t("analytics.activeOrders"), value: overview.active_work_orders, icon: ClipboardList },
    { label: t("analytics.lowStock"), value: overview.low_stock_parts, icon: Boxes },
    { label: t("analytics.overdueReminders"), value: overview.overdue_reminders, icon: Wrench },
    { label: t("analytics.criticalFindings"), value: overview.unresolved_critical_findings, icon: AlertTriangle },
    { label: t("analytics.health"), value: overview.inspection_average_health == null ? "—" : `%${formatNumber(overview.inspection_average_health, language)}`, icon: HeartPulse },
  ];

  return (
    <div className="page-stack analytics-page">
      <section className="analytics-hero">
        <div>
          <span className="section-kicker">{t("analytics.kicker")}</span>
          <h2>{t("analytics.title")}</h2>
          <p>{t("analytics.subtitle")}</p>
          <small>{t("analytics.currentWindow", { start: periodDate(overview.period_start, language), end: periodDate(overview.period_end, language) })} · {t("analytics.compareNote")}</small>
        </div>
        <div className="period-control" role="group" aria-label={t("analytics.period")}>
          <span>{t("analytics.period")}</span>
          <div>{PERIODS.map((item) => <button key={item} type="button" className={period === item ? "active" : ""} onClick={() => setPeriod(item)} disabled={loading}>{t("analytics.days", { count: item })}</button>)}</div>
        </div>
      </section>

      <section className="analytics-kpi-grid" aria-busy={loading}>
        {kpis.map(({ key, label, metric, icon: Icon, tone, format, goodWhenUp }) => (
          <article className="analytics-kpi" key={key}>
            <span className={`metric-icon ${tone}`}><Icon size={20} /></span>
            <span className="analytics-kpi-label">{label}</span>
            <strong>{metric.current == null ? "—" : format(metric.current)}</strong>
            {metric.denominator != null && <small className="analytics-base">{t("analytics.rateBase", { numerator: metric.numerator ?? 0, denominator: metric.denominator })}</small>}
            <Delta metric={metric} goodWhenUp={goodWhenUp} />
          </article>
        ))}
      </section>

      <section className="analytics-chart-grid">
        <article className="panel revenue-panel">
          <div className="panel-heading"><div><span className="section-kicker">{t("analytics.period")}</span><h3>{t("analytics.revenueTrend")}</h3><p className="panel-copy">{t("analytics.revenueHelp")}</p></div></div>
          <RevenueChart rows={overview.series} />
        </article>
        <article className="panel completed-panel">
          <div className="panel-heading"><div><span className="section-kicker">{t("analytics.period")}</span><h3>{t("analytics.completedTrend")}</h3><p className="panel-copy">{t("analytics.completedHelp")}</p></div></div>
          <CompletedChart rows={overview.series} />
          <div className="completion-total"><ClipboardCheck size={20} /><span><strong>{formatNumber(overview.completed_orders.current, language)}</strong>{t("analytics.completedOrders")}</span></div>
        </article>
      </section>

      <section className="panel snapshot-panel">
        <div className="panel-heading"><div><span className="section-kicker">{t("analytics.snapshot")}</span><h3>{t("analytics.attention")}</h3><p className="panel-copy">{t("analytics.snapshotHelp")}</p></div></div>
        <div className="snapshot-grid">{snapshots.map(({ label, value, icon: Icon }) => <div key={label}><Icon size={19} /><strong>{value}</strong><span>{label}</span></div>)}</div>
      </section>

      <section className="analytics-detail-grid">
        <article className="panel">
          <div className="panel-heading"><div><span className="section-kicker">{t("analytics.snapshot")}</span><h3>{t("analytics.statusDistribution")}</h3></div></div>
          <div className="analytics-bars">{overview.work_order_statuses.map((item) => <div key={item.key}><span>{t(`status.${item.key}`)}</span><div><i style={{ width: `${totalOrders ? (item.count / totalOrders) * 100 : 0}%` }} /></div><strong>{item.count}</strong></div>)}</div>
        </article>
        <article className="panel">
          <div className="panel-heading"><div><span className="section-kicker">{t("analytics.period")}</span><h3>{t("analytics.estimateFunnel")}</h3></div></div>
          <div className="analytics-bars funnel-bars">{overview.estimate_funnel.map((item) => <div key={item.key}><span>{t(`estimate.status.${item.key}`)}</span><div><i style={{ width: `${(item.count / maxFunnel) * 100}%` }} /></div><strong>{item.count}</strong></div>)}</div>
        </article>
        <article className="panel">
          <div className="panel-heading"><div><span className="section-kicker">{t("analytics.period")}</span><h3>{t("analytics.topServices")}</h3></div></div>
          {overview.top_services.length ? <div className="analytics-bars service-bars">{overview.top_services.map((item) => <div key={item.key}><span title={item.key}>{item.key}</span><div><i style={{ width: `${(item.count / maxService) * 100}%` }} /></div><strong>{item.count}</strong></div>)}</div> : <p className="analytics-empty">{t("analytics.noServices")}</p>}
        </article>
      </section>

      <details className="analytics-methods"><summary>{t("analytics.definitions")}</summary><p>{t("analytics.definitionsText")}</p></details>
    </div>
  );
}
