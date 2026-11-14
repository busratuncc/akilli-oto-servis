import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import {
  CheckCircle2,
  ClipboardCopy,
  FileCheck2,
  Link2,
  Plus,
  ReceiptText,
  Send,
  ShieldCheck,
  Trash2,
  XCircle,
} from "lucide-react";
import { useNavigate } from "react-router-dom";

import { api } from "../api";
import { useI18n } from "../i18n";
import type { Estimate, InventoryPart, InvoiceItemType, Vehicle, WorkOrder } from "../types";
import { formatCurrency, formatDateOnly, orderCode } from "../utils";

type DraftLine = {
  item_type: InvoiceItemType;
  inventory_part_id: string | null;
  description: string;
  quantity: string;
  unit_price: string;
};

type Props = {
  vehicles: Vehicle[];
  orders: WorkOrder[];
  notify: (message: string) => void;
  reportError: (message: string) => void;
};

const emptyLine = (): DraftLine => ({
  item_type: "labor",
  inventory_part_id: null,
  description: "",
  quantity: "1",
  unit_price: "",
});

function defaultValidUntil() {
  const date = new Date();
  date.setDate(date.getDate() + 7);
  return date.toISOString().slice(0, 10);
}

export function EstimatesPage({ vehicles, orders, notify, reportError }: Props) {
  const { language, t } = useI18n();
  const navigate = useNavigate();
  const [estimates, setEstimates] = useState<Estimate[]>([]);
  const [parts, setParts] = useState<InventoryPart[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);
  const [shareLink, setShareLink] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [workOrderId, setWorkOrderId] = useState("");
  const [lines, setLines] = useState<DraftLine[]>([emptyLine()]);
  const [discount, setDiscount] = useState("0");
  const [taxRate, setTaxRate] = useState("20");
  const [validUntil, setValidUntil] = useState(defaultValidUntil);
  const [notes, setNotes] = useState("");

  const load = useCallback(async () => {
    try {
      const [estimateData, partData] = await Promise.all([
        api.listEstimates(),
        api.listInventoryParts(),
      ]);
      setEstimates(estimateData);
      setParts(partData.filter((part) => part.active));
      setSelectedId((current) => current && estimateData.some((item) => item.id === current)
        ? current
        : estimateData[0]?.id ?? "");
    } catch (error) {
      reportError(error instanceof Error ? error.message : t("estimate.loadError"));
    } finally {
      setLoading(false);
    }
  }, [reportError, t]);

  useEffect(() => { void load(); }, [load]);

  const vehicleMap = useMemo(() => new Map(vehicles.map((vehicle) => [vehicle.id, vehicle])), [vehicles]);
  const orderMap = useMemo(() => new Map(orders.map((order) => [order.id, order])), [orders]);
  const selected = estimates.find((item) => item.id === selectedId) ?? null;
  const convertedOrders = useMemo(
    () => new Set(estimates.filter((item) => item.status === "converted").map((item) => item.work_order_id)),
    [estimates],
  );
  const availableOrders = orders.filter((order) => !convertedOrders.has(order.id));
  const metrics = useMemo(() => ({
    draft: estimates.filter((item) => item.status === "draft").length,
    sent: estimates.filter((item) => item.status === "sent").length,
    approved: estimates.filter((item) => item.status === "approved").length,
    rejected: estimates.filter((item) => item.status === "rejected").length,
  }), [estimates]);
  const preview = useMemo(() => {
    const subtotal = lines.reduce((sum, line) => sum + Number(line.quantity || 0) * Number(line.unit_price || 0), 0);
    const taxable = Math.max(0, subtotal - Number(discount || 0));
    const tax = taxable * Number(taxRate || 0) / 100;
    return { subtotal, tax, total: taxable + tax };
  }, [discount, lines, taxRate]);

  function updateLine(index: number, field: keyof DraftLine, value: string | null) {
    setLines((current) => current.map((line, lineIndex) => lineIndex === index ? { ...line, [field]: value } : line));
  }

  function selectPart(index: number, partId: string) {
    const part = parts.find((item) => item.id === partId);
    setLines((current) => current.map((line, lineIndex) => lineIndex === index ? {
      ...line,
      inventory_part_id: part?.id ?? null,
      description: part?.name ?? line.description,
      unit_price: part?.sale_price ?? line.unit_price,
    } : line));
  }

  async function createEstimate(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    try {
      const created = await api.createEstimate(workOrderId, {
        line_items: lines,
        discount_amount: discount || "0",
        tax_rate: taxRate || "0",
        notes: notes.trim() || null,
        valid_until: validUntil,
      });
      setShowForm(false);
      setWorkOrderId("");
      setLines([emptyLine()]);
      setDiscount("0");
      setTaxRate("20");
      setValidUntil(defaultValidUntil());
      setNotes("");
      setSelectedId(created.id);
      notify(t("estimate.created", { number: created.estimate_number }));
      await load();
    } catch (error) {
      reportError(error instanceof Error ? error.message : t("estimate.createError"));
    } finally {
      setSaving(false);
    }
  }

  async function sendEstimate() {
    if (!selected) return;
    setSaving(true);
    try {
      const result = await api.sendEstimate(selected.id);
      setShareLink(result.approval_url);
      setEstimates((current) => current.map((item) => item.id === result.estimate.id ? result.estimate : item));
      notify(t("estimate.sent"));
    } catch (error) {
      reportError(error instanceof Error ? error.message : t("estimate.sendError"));
    } finally {
      setSaving(false);
    }
  }

  async function copyLink() {
    try {
      await navigator.clipboard.writeText(shareLink);
      notify(t("estimate.linkCopied"));
    } catch {
      reportError(t("estimate.copyError"));
    }
  }

  async function convertToInvoice() {
    if (!selected) return;
    setSaving(true);
    try {
      await api.convertEstimateToInvoice(selected.id, dueDate || null);
      notify(t("estimate.converted"));
      await load();
      navigate("/finance");
    } catch (error) {
      reportError(error instanceof Error ? error.message : t("estimate.convertError"));
    } finally {
      setSaving(false);
    }
  }

  return <div className="page-stack estimate-page">
    <section className="page-title-row"><div><span className="section-kicker">{t("estimate.kicker")}</span><h2>{t("estimate.title")}</h2><p>{t("estimate.subtitle")}</p></div><button className="primary-button" onClick={() => setShowForm((value) => !value)}><Plus size={17} /> {t("estimate.new")}</button></section>

    <section className="metric-grid estimate-metrics">
      <div className="metric-card"><span className="metric-icon blue"><ReceiptText size={21} /></span><div><strong>{metrics.draft}</strong><span>{t("estimate.metricDraft")}</span></div></div>
      <div className="metric-card"><span className="metric-icon orange"><Send size={21} /></span><div><strong>{metrics.sent}</strong><span>{t("estimate.metricSent")}</span></div></div>
      <div className="metric-card"><span className="metric-icon green"><CheckCircle2 size={21} /></span><div><strong>{metrics.approved}</strong><span>{t("estimate.metricApproved")}</span></div></div>
      <div className="metric-card"><span className="metric-icon purple"><XCircle size={21} /></span><div><strong>{metrics.rejected}</strong><span>{t("estimate.metricRejected")}</span></div></div>
    </section>

    {showForm && <section className="panel form-panel"><div className="panel-heading"><div><span className="section-kicker">{t("estimate.formKicker")}</span><h3>{t("estimate.formTitle")}</h3></div><ShieldCheck size={22} /></div>
      <form className="invoice-form" onSubmit={createEstimate}>
        <div className="estimate-form-top"><label>{t("estimate.workOrder")}<select required value={workOrderId} onChange={(event) => setWorkOrderId(event.target.value)}><option value="">{t("common.select")}</option>{availableOrders.map((order) => { const vehicle = vehicleMap.get(order.vehicle_id); return <option value={order.id} key={order.id}>{orderCode(order.id)} · {vehicle?.anonymous_code ?? "—"} · {order.customer_complaint}</option>; })}</select></label><label>{t("estimate.validUntil")}<input required type="date" min={new Date().toISOString().slice(0, 10)} value={validUntil} onChange={(event) => setValidUntil(event.target.value)} /></label></div>
        <div className="invoice-lines"><div className="invoice-line-head"><strong>{t("estimate.items")}</strong><button type="button" className="ghost-button" onClick={() => setLines((current) => [...current, emptyLine()])}><Plus size={15} /> {t("estimate.addItem")}</button></div>{lines.map((line, index) => <div className="invoice-line" key={index}>
          <label>{t("finance.itemType")}<select value={line.item_type} onChange={(event) => { const type = event.target.value as InvoiceItemType; setLines((current) => current.map((item, i) => i === index ? { ...item, item_type: type, inventory_part_id: type === "part" ? item.inventory_part_id : null } : item)); }}><option value="labor">{t("finance.labor")}</option><option value="part">{t("finance.part")}</option><option value="other">{t("finance.other")}</option></select></label>
          <label>{t("finance.description")}{line.item_type === "part" && <select className="stock-part-select" value={line.inventory_part_id ?? ""} onChange={(event) => selectPart(index, event.target.value)}><option value="">{t("finance.manualPart")}</option>{parts.map((part) => <option value={part.id} key={part.id}>{part.sku} · {part.name} · {part.stock_quantity}</option>)}</select>}<input required minLength={2} value={line.description} onChange={(event) => updateLine(index, "description", event.target.value)} /></label>
          <label>{t("finance.quantity")}<input required type="number" min="0.01" step="0.01" value={line.quantity} onChange={(event) => updateLine(index, "quantity", event.target.value)} /></label><label>{t("finance.unitPrice")}<input required type="number" min="0" step="0.01" value={line.unit_price} onChange={(event) => updateLine(index, "unit_price", event.target.value)} /></label><strong className="line-total">{formatCurrency(Number(line.quantity || 0) * Number(line.unit_price || 0), language)}</strong><button type="button" className="line-delete" disabled={lines.length === 1} onClick={() => setLines((current) => current.filter((_, i) => i !== index))}><Trash2 size={16} /></button>
        </div>)}</div>
        <div className="invoice-bottom-grid"><label>{t("finance.discount")}<input type="number" min="0" step="0.01" value={discount} onChange={(event) => setDiscount(event.target.value)} /></label><label>{t("finance.taxRate")}<input type="number" min="0" max="100" step="0.01" value={taxRate} onChange={(event) => setTaxRate(event.target.value)} /></label><label className="span-2">{t("estimate.notes")}<textarea rows={2} value={notes} onChange={(event) => setNotes(event.target.value)} /></label><div className="invoice-preview"><span>{t("finance.subtotal")}<strong>{formatCurrency(preview.subtotal, language)}</strong></span><span>{t("finance.tax")}<strong>{formatCurrency(preview.tax, language)}</strong></span><span className="preview-total">{t("finance.total")}<strong>{formatCurrency(preview.total, language)}</strong></span></div></div>
        <div className="form-actions"><button type="button" className="ghost-button" onClick={() => setShowForm(false)}>{t("common.cancel")}</button><button className="primary-button" disabled={saving}>{saving ? t("common.saving") : t("estimate.create")}</button></div>
      </form>
    </section>}

    <section className="estimate-layout"><div className="panel"><div className="list-toolbar"><div><span className="section-kicker">{t("estimate.records", { count: estimates.length })}</span><h3>{t("estimate.listTitle")}</h3></div></div>{loading ? <div className="empty-state"><p>{t("estimate.loading")}</p></div> : <div className="estimate-list">{estimates.map((item) => { const order = orderMap.get(item.work_order_id); const vehicle = order ? vehicleMap.get(order.vehicle_id) : null; return <button className={`estimate-row ${selectedId === item.id ? "selected" : ""}`} key={item.id} onClick={() => { setSelectedId(item.id); setShareLink(""); }}><span className="estimate-row-icon"><FileCheck2 size={18} /></span><span><strong>{item.estimate_number}</strong><small>{vehicle?.anonymous_code ?? orderCode(item.work_order_id)} · {formatDateOnly(item.valid_until, language)}</small></span><i className={`estimate-status estimate-status-${item.status}`}>{t(`estimate.status.${item.status}`)}</i><strong>{formatCurrency(item.total_amount, language)}</strong></button>; })}{estimates.length === 0 && <div className="empty-state tall-empty"><FileCheck2 size={32} /><p>{t("estimate.empty")}</p><small>{t("estimate.emptyHelp")}</small></div>}</div>}</div>

      <aside className="panel estimate-detail">{!selected ? <div className="empty-state tall-empty"><FileCheck2 size={32} /><p>{t("estimate.select")}</p></div> : <><div className="detail-head"><div><span className="section-kicker">{selected.estimate_number}</span><h3>{formatCurrency(selected.total_amount, language)}</h3></div><span className={`estimate-status estimate-status-${selected.status}`}>{t(`estimate.status.${selected.status}`)}</span></div><div className="estimate-validity"><span>{t("estimate.version")} <strong>v{selected.version}</strong></span><span>{t("estimate.validUntil")} <strong>{formatDateOnly(selected.valid_until, language)}</strong></span></div><div className="invoice-detail-lines">{selected.line_items.map((item) => <div key={item.id}><span><strong>{item.description}</strong><small>{t(`finance.${item.item_type}`)} · {item.quantity} × {formatCurrency(item.unit_price, language)}</small></span><strong>{formatCurrency(item.line_total, language)}</strong></div>)}</div><div className="invoice-totals"><span>{t("finance.subtotal")}<strong>{formatCurrency(selected.subtotal, language)}</strong></span><span>{t("finance.discount")}<strong>-{formatCurrency(selected.discount_amount, language)}</strong></span><span>{t("finance.tax")} ({selected.tax_rate}%)<strong>{formatCurrency(selected.tax_amount, language)}</strong></span></div>{selected.notes && <div className="estimate-note">{selected.notes}</div>}{selected.response_note && <div className="estimate-response"><strong>{t("estimate.customerNote")}</strong><p>{selected.response_note}</p></div>}
        {shareLink && <div className="share-link-box"><span><Link2 size={16} /> {t("estimate.oneTimeLink")}</span><input readOnly value={shareLink} /><button className="secondary-button" onClick={() => void copyLink()}><ClipboardCopy size={16} /> {t("estimate.copy")}</button><small>{t("estimate.linkSecurity")}</small></div>}
        {["draft", "sent", "rejected", "expired"].includes(selected.status) && <button className="primary-button full-button" disabled={saving} onClick={() => void sendEstimate()}><Send size={16} /> {selected.status === "sent" ? t("estimate.renewLink") : t("estimate.sendApproval")}</button>}
        {selected.status === "approved" && <div className="estimate-convert"><div className="quality-note"><CheckCircle2 size={17} /> {t("estimate.approvedHelp")}</div><label>{t("finance.dueDate")}<input type="date" value={dueDate} onChange={(event) => setDueDate(event.target.value)} /></label><button className="primary-button full-button" disabled={saving} onClick={() => void convertToInvoice()}><ReceiptText size={16} /> {t("estimate.convert")}</button></div>}
        {selected.status === "converted" && <button className="secondary-button full-button" onClick={() => navigate("/finance")}><ReceiptText size={16} /> {t("estimate.openInvoice")}</button>}
      </>}</aside></section>
  </div>;
}
