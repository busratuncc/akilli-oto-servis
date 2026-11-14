import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  Banknote,
  CircleDollarSign,
  CreditCard,
  Plus,
  ReceiptText,
  Trash2,
  WalletCards,
} from "lucide-react";
import { useLocation, useNavigate } from "react-router-dom";

import { api } from "../api";
import { useI18n } from "../i18n";
import type {
  FinanceSummary,
  Invoice,
  InvoiceItemType,
  InventoryPart,
  PaymentMethod,
  Vehicle,
  WorkOrder,
} from "../types";
import { formatCurrency, formatDate, formatDateOnly, orderCode } from "../utils";

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

export function FinancePage({ vehicles, orders, notify, reportError }: Props) {
  const { language, t } = useI18n();
  const location = useLocation();
  const navigate = useNavigate();
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [inventoryParts, setInventoryParts] = useState<InventoryPart[]>([]);
  const [summary, setSummary] = useState<FinanceSummary | null>(null);
  const [selectedId, setSelectedId] = useState("");
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [workOrderId, setWorkOrderId] = useState("");
  const [lines, setLines] = useState<DraftLine[]>([emptyLine()]);
  const [discount, setDiscount] = useState("0");
  const [taxRate, setTaxRate] = useState("20");
  const [dueDate, setDueDate] = useState("");
  const [notes, setNotes] = useState("");
  const [payment, setPayment] = useState<{
    amount: string;
    method: PaymentMethod;
    reference: string;
    notes: string;
  }>({ amount: "", method: "cash", reference: "", notes: "" });
  const [recording, setRecording] = useState(false);

  const loadFinance = useCallback(async () => {
    try {
      const [invoiceData, summaryData, partData] = await Promise.all([
        api.listInvoices(),
        api.financeSummary(),
        api.listInventoryParts(),
      ]);
      setInvoices(invoiceData);
      setSummary(summaryData);
      setInventoryParts(partData.filter((part) => part.active));
      setSelectedId((current) =>
        current && invoiceData.some((invoice) => invoice.id === current)
          ? current
          : invoiceData[0]?.id ?? "",
      );
    } catch (error) {
      reportError(error instanceof Error ? error.message : t("finance.loadError"));
    } finally {
      setLoading(false);
    }
  }, [reportError, t]);

  useEffect(() => {
    void loadFinance();
  }, [loadFinance]);

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    if (params.get("payment") !== "success") return;
    notify(t("card.paymentSuccess"));
    void loadFinance();
    navigate("/finance", { replace: true });
  }, [loadFinance, location.search, navigate, notify, t]);

  const vehicleMap = useMemo(
    () => new Map(vehicles.map((vehicle) => [vehicle.id, vehicle])),
    [vehicles],
  );
  const orderMap = useMemo(() => new Map(orders.map((order) => [order.id, order])), [orders]);
  const invoicedOrderIds = useMemo(
    () => new Set(invoices.map((invoice) => invoice.work_order_id)),
    [invoices],
  );
  const availableOrders = orders.filter((order) => !invoicedOrderIds.has(order.id));
  const selected = invoices.find((invoice) => invoice.id === selectedId) ?? null;

  const preview = useMemo(() => {
    const subtotal = lines.reduce((sum, line) => {
      const lineTotal = Math.round(Number(line.quantity || 0) * Number(line.unit_price || 0) * 100) / 100;
      return sum + lineTotal;
    }, 0);
    const taxable = Math.max(0, subtotal - Number(discount || 0));
    const tax = Math.round(taxable * Number(taxRate || 0)) / 100;
    return { subtotal, tax, total: taxable + tax };
  }, [discount, lines, taxRate]);

  function updateLine(index: number, field: keyof DraftLine, value: string) {
    setLines((current) => current.map((line, lineIndex) =>
      lineIndex === index ? { ...line, [field]: value } : line,
    ));
  }

  function changeItemType(index: number, itemType: InvoiceItemType) {
    setLines((current) => current.map((line, lineIndex) =>
      lineIndex === index
        ? { ...line, item_type: itemType, inventory_part_id: itemType === "part" ? line.inventory_part_id : null }
        : line,
    ));
  }

  function selectStockPart(index: number, partId: string) {
    const part = inventoryParts.find((item) => item.id === partId);
    setLines((current) => current.map((line, lineIndex) =>
      lineIndex === index
        ? {
            ...line,
            inventory_part_id: part?.id ?? null,
            description: part?.name ?? line.description,
            unit_price: part?.sale_price ?? line.unit_price,
          }
        : line,
    ));
  }

  function resetInvoiceForm() {
    setWorkOrderId("");
    setLines([emptyLine()]);
    setDiscount("0");
    setTaxRate("20");
    setDueDate("");
    setNotes("");
  }

  async function submitInvoice(event: FormEvent) {
    event.preventDefault();
    if (!workOrderId) return;
    setSaving(true);
    try {
      const created = await api.createInvoice(workOrderId, {
        line_items: lines,
        discount_amount: discount || "0",
        tax_rate: taxRate || "0",
        notes: notes.trim() || null,
        due_date: dueDate || null,
      });
      resetInvoiceForm();
      setShowForm(false);
      setSelectedId(created.id);
      notify(t("finance.created", { number: created.invoice_number }));
      await loadFinance();
    } catch (error) {
      reportError(error instanceof Error ? error.message : t("finance.createError"));
    } finally {
      setSaving(false);
    }
  }

  async function submitPayment(event: FormEvent) {
    event.preventDefault();
    if (!selected) return;
    setRecording(true);
    try {
      await api.recordPayment(selected.id, {
        amount: payment.amount,
        method: payment.method,
        reference: payment.reference.trim() || null,
        notes: payment.notes.trim() || null,
      });
      setPayment({ amount: "", method: "cash", reference: "", notes: "" });
      notify(t("finance.paymentSaved"));
      await loadFinance();
    } catch (error) {
      reportError(error instanceof Error ? error.message : t("finance.paymentError"));
    } finally {
      setRecording(false);
    }
  }

  function selectInvoice(invoice: Invoice) {
    setSelectedId(invoice.id);
    setPayment((current) => ({ ...current, amount: invoice.balance_due }));
  }

  return (
    <div className="page-stack">
      <section className="page-title-row">
        <div>
          <span className="section-kicker">{t("finance.kicker")}</span>
          <h2>{t("finance.title")}</h2>
          <p>{t("finance.subtitle")}</p>
        </div>
        <button className="primary-button" onClick={() => setShowForm((value) => !value)}>
          <Plus size={18} /> {t("finance.newInvoice")}
        </button>
      </section>

      <section className="metric-grid finance-metrics">
        <div className="metric-card"><span className="metric-icon blue"><ReceiptText size={22} /></span><div><strong>{formatCurrency(summary?.invoiced_total ?? 0, language)}</strong><span>{t("finance.invoiced")}</span></div></div>
        <div className="metric-card"><span className="metric-icon green"><Banknote size={22} /></span><div><strong>{formatCurrency(summary?.collected_total ?? 0, language)}</strong><span>{t("finance.collected")}</span></div></div>
        <div className="metric-card"><span className="metric-icon orange"><WalletCards size={22} /></span><div><strong>{formatCurrency(summary?.outstanding_total ?? 0, language)}</strong><span>{t("finance.outstanding")}</span></div></div>
        <div className="metric-card"><span className="metric-icon purple"><AlertTriangle size={22} /></span><div><strong>{summary?.overdue_invoices ?? 0}</strong><span>{t("finance.overdue")}</span></div></div>
      </section>

      <div className="payment-safety finance-scope-notice"><CreditCard size={18} /><span>{t("finance.scopeNotice")}</span></div>

      {showForm && (
        <section className="panel form-panel">
          <div className="panel-heading"><div><span className="section-kicker">{t("finance.invoiceForm")}</span><h3>{t("finance.invoiceDetails")}</h3></div></div>
          {availableOrders.length === 0 ? (
            <div className="inline-warning">{t("finance.noAvailableOrder")}</div>
          ) : (
            <form className="invoice-form" onSubmit={submitInvoice}>
              <label>{t("finance.workOrder")}
                <select required value={workOrderId} onChange={(event) => setWorkOrderId(event.target.value)}>
                  <option value="">{t("common.select")}</option>
                  {availableOrders.map((order) => {
                    const vehicle = vehicleMap.get(order.vehicle_id);
                    return <option key={order.id} value={order.id}>{orderCode(order.id)} · {vehicle?.anonymous_code ?? "—"} · {order.customer_complaint}</option>;
                  })}
                </select>
              </label>

              <div className="invoice-lines">
                <div className="invoice-line-head"><strong>{t("finance.items")}</strong><button type="button" className="ghost-button" onClick={() => setLines((current) => [...current, emptyLine()])}><Plus size={16} /> {t("finance.addItem")}</button></div>
                {lines.map((line, index) => (
                  <div className="invoice-line" key={index}>
                    <label>{t("finance.itemType")}<select value={line.item_type} onChange={(event) => changeItemType(index, event.target.value as InvoiceItemType)}><option value="labor">{t("finance.labor")}</option><option value="part">{t("finance.part")}</option><option value="other">{t("finance.other")}</option></select></label>
                    <label>{t("finance.description")}{line.item_type === "part" && <select className="stock-part-select" value={line.inventory_part_id ?? ""} onChange={(event) => selectStockPart(index, event.target.value)}><option value="">{t("finance.manualPart")}</option>{inventoryParts.map((part) => <option key={part.id} value={part.id}>{part.sku} · {part.name} · {part.stock_quantity} {t(`inventory.unit.${part.unit}`)}</option>)}</select>}<input required minLength={2} value={line.description} onChange={(event) => updateLine(index, "description", event.target.value)} placeholder={t("finance.descriptionPlaceholder")} /></label>
                    <label>{t("finance.quantity")}<input required type="number" min="0.01" step="0.01" value={line.quantity} onChange={(event) => updateLine(index, "quantity", event.target.value)} /></label>
                    <label>{t("finance.unitPrice")}<input required type="number" min="0" step="0.01" value={line.unit_price} onChange={(event) => updateLine(index, "unit_price", event.target.value)} /></label>
                    <strong className="line-total">{formatCurrency(Number(line.quantity || 0) * Number(line.unit_price || 0), language)}</strong>
                    <button type="button" className="line-delete" aria-label={t("finance.removeItem")} disabled={lines.length === 1} onClick={() => setLines((current) => current.filter((_, lineIndex) => lineIndex !== index))}><Trash2 size={17} /></button>
                  </div>
                ))}
              </div>

              <div className="invoice-bottom-grid">
                <label>{t("finance.discount")}<input type="number" min="0" step="0.01" value={discount} onChange={(event) => setDiscount(event.target.value)} /></label>
                <label>{t("finance.taxRate")}<input type="number" min="0" max="100" step="0.01" value={taxRate} onChange={(event) => setTaxRate(event.target.value)} /></label>
                <label>{t("finance.dueDate")}<input type="date" value={dueDate} onChange={(event) => setDueDate(event.target.value)} /></label>
                <label className="span-2">{t("finance.notes")}<textarea rows={2} value={notes} onChange={(event) => setNotes(event.target.value)} /></label>
                <div className="invoice-preview"><span>{t("finance.subtotal")}<strong>{formatCurrency(preview.subtotal, language)}</strong></span><span>{t("finance.tax")}<strong>{formatCurrency(preview.tax, language)}</strong></span><span className="preview-total">{t("finance.total")}<strong>{formatCurrency(preview.total, language)}</strong></span></div>
              </div>
              <div className="form-actions"><button type="button" className="ghost-button" onClick={() => setShowForm(false)}>{t("common.cancel")}</button><button className="primary-button" disabled={saving}>{saving ? t("common.saving") : t("finance.createInvoice")}</button></div>
            </form>
          )}
        </section>
      )}

      <section className="finance-layout">
        <div className="panel">
          <div className="list-toolbar"><div><span className="section-kicker">{t("finance.records", { count: invoices.length })}</span><h3>{t("finance.invoices")}</h3></div></div>
          {loading ? <div className="empty-state"><p>{t("finance.loading")}</p></div> : (
            <div className="invoice-list">
              {invoices.map((invoice) => {
                const order = orderMap.get(invoice.work_order_id);
                const vehicle = order ? vehicleMap.get(order.vehicle_id) : null;
                return (
                  <button key={invoice.id} className={`invoice-row ${selectedId === invoice.id ? "selected" : ""}`} onClick={() => selectInvoice(invoice)}>
                    <span className="invoice-row-icon"><ReceiptText size={19} /></span>
                    <span className="invoice-row-main"><strong>{invoice.invoice_number}</strong><small>{vehicle?.anonymous_code ?? orderCode(invoice.work_order_id)} · {formatDate(invoice.issued_at, language)}</small></span>
                    <span className={`invoice-status status-${invoice.status}`}>{t(`finance.status.${invoice.status}`)}</span>
                    <span className="invoice-row-money"><strong>{formatCurrency(invoice.total_amount, language)}</strong><small>{t("finance.balance")}: {formatCurrency(invoice.balance_due, language)}</small></span>
                  </button>
                );
              })}
              {invoices.length === 0 && <div className="empty-state tall-empty"><ReceiptText size={32} /><p>{t("finance.noInvoices")}</p><small>{t("finance.noInvoicesHelp")}</small></div>}
            </div>
          )}
        </div>

        <aside className="panel invoice-detail">
          {!selected ? <div className="empty-state tall-empty"><CircleDollarSign size={32} /><p>{t("finance.selectInvoice")}</p></div> : (
            <>
              <div className="detail-head"><div><span className="section-kicker">{selected.invoice_number}</span><h3>{formatCurrency(selected.total_amount, language)}</h3></div><span className={`invoice-status status-${selected.status}`}>{t(`finance.status.${selected.status}`)}</span></div>
              <div className="invoice-balance-bar"><span><small>{t("finance.paid")}</small><strong>{formatCurrency(selected.paid_amount, language)}</strong></span><span><small>{t("finance.balance")}</small><strong>{formatCurrency(selected.balance_due, language)}</strong></span></div>
              {selected.due_date && <p className="due-date">{t("finance.dueDate")}: <strong>{formatDateOnly(selected.due_date, language)}</strong></p>}
              <div className="invoice-detail-lines">
                {selected.line_items.map((item) => <div key={item.id}><span><strong>{item.description}</strong><small>{t(`finance.${item.item_type}`)} · {item.quantity} × {formatCurrency(item.unit_price, language)}</small></span><strong>{formatCurrency(item.line_total, language)}</strong></div>)}
              </div>
              <div className="invoice-totals"><span>{t("finance.subtotal")}<strong>{formatCurrency(selected.subtotal, language)}</strong></span><span>{t("finance.discount")}<strong>-{formatCurrency(selected.discount_amount, language)}</strong></span><span>{t("finance.tax")} ({selected.tax_rate}%)<strong>{formatCurrency(selected.tax_amount, language)}</strong></span></div>

              {Number(selected.balance_due) > 0 && (
                <>
                <div className="test-card-cta"><span className="settings-card-icon"><CreditCard size={20} /></span><span><strong>{t("card.testBankPay")}</strong><small>{t("card.testBankPayHelp")}</small></span><button className="secondary-button" onClick={() => navigate(`/finance/card-payment/${selected.id}`)}>{t("card.openForm")}</button></div>
                <form className="payment-form" onSubmit={submitPayment}>
                  <div className="panel-heading"><div><span className="section-kicker">{t("finance.payment")}</span><h3>{t("finance.recordPayment")}</h3></div></div>
                  <label>{t("finance.amount")}<div className="amount-fill"><input required type="number" min="0.01" max={selected.balance_due} step="0.01" value={payment.amount} onChange={(event) => setPayment({ ...payment, amount: event.target.value })} /><button type="button" onClick={() => setPayment({ ...payment, amount: selected.balance_due })}>{t("finance.fillBalance")}</button></div></label>
                  <label>{t("finance.method")}<select value={payment.method} onChange={(event) => setPayment({ ...payment, method: event.target.value as PaymentMethod })}><option value="cash">{t("finance.method.cash")}</option><option value="card_pos">{t("finance.method.card_pos")}</option><option value="bank_transfer">{t("finance.method.bank_transfer")}</option><option value="other">{t("finance.method.other")}</option></select></label>
                  {payment.method === "card_pos" && <div className="payment-safety"><CreditCard size={17} /><span>{t("finance.posSafety")}</span></div>}
                  <label>{t("finance.reference")}<input value={payment.reference} onChange={(event) => setPayment({ ...payment, reference: event.target.value })} placeholder={t("finance.referencePlaceholder")} /></label>
                  <label>{t("finance.notes")}<textarea rows={2} value={payment.notes} onChange={(event) => setPayment({ ...payment, notes: event.target.value })} /></label>
                  <button className="primary-button full-button" disabled={recording}>{recording ? t("common.saving") : t("finance.savePayment")}</button>
                </form>
                </>
              )}

              <div className="payment-history"><strong>{t("finance.paymentHistory")}</strong>{selected.payments.length === 0 ? <small>{t("finance.noPayments")}</small> : selected.payments.map((item) => <div key={item.id}><span><Banknote size={16} /><span><strong>{t(`finance.method.${item.method}`)}</strong><small>{formatDate(item.received_at, language)}{item.reference ? ` · ${item.reference}` : ""}</small></span></span><strong>{formatCurrency(item.amount, language)}</strong></div>)}</div>
            </>
          )}
        </aside>
      </section>
    </div>
  );
}
