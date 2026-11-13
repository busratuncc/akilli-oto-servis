import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  ArrowDownToLine,
  ArrowUpFromLine,
  Boxes,
  Coins,
  PackageCheck,
  PackageX,
  Plus,
  Search,
} from "lucide-react";

import { api } from "../api";
import { useI18n } from "../i18n";
import type { InventoryPart, InventorySummary, StockMovement } from "../types";
import { formatCurrency, formatDate } from "../utils";

type Props = {
  notify: (message: string) => void;
  reportError: (message: string) => void;
};

const emptyPart = {
  sku: "",
  name: "",
  brand: "",
  category: "",
  unit: "piece",
  initial_quantity: "0",
  low_stock_threshold: "1",
  purchase_price: "0",
  sale_price: "0",
};

type EditForm = Pick<InventoryPart, "sku" | "name" | "unit"> & {
  brand: string;
  category: string;
  low_stock_threshold: string;
  purchase_price: string;
  sale_price: string;
  active: boolean;
};

function editFromPart(part: InventoryPart): EditForm {
  return {
    sku: part.sku,
    name: part.name,
    brand: part.brand ?? "",
    category: part.category ?? "",
    unit: part.unit,
    low_stock_threshold: part.low_stock_threshold,
    purchase_price: part.purchase_price,
    sale_price: part.sale_price,
    active: part.active,
  };
}

export function InventoryPage({ notify, reportError }: Props) {
  const { language, t } = useI18n();
  const [parts, setParts] = useState<InventoryPart[]>([]);
  const [movements, setMovements] = useState<StockMovement[]>([]);
  const [summary, setSummary] = useState<InventorySummary | null>(null);
  const [selectedId, setSelectedId] = useState("");
  const [edit, setEdit] = useState<EditForm | null>(null);
  const [form, setForm] = useState(emptyPart);
  const [movement, setMovement] = useState({ movement_type: "stock_in" as "stock_in" | "stock_out", quantity: "", notes: "" });
  const [query, setQuery] = useState("");
  const [lowOnly, setLowOnly] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);

  const loadInventory = useCallback(async () => {
    try {
      const [partData, movementData, summaryData] = await Promise.all([
        api.listInventoryParts(),
        api.listStockMovements(),
        api.inventorySummary(),
      ]);
      setParts(partData);
      setMovements(movementData);
      setSummary(summaryData);
      setSelectedId((current) => {
        const next = current && partData.some((part) => part.id === current)
          ? current
          : partData[0]?.id ?? "";
        const selectedPart = partData.find((part) => part.id === next);
        if (selectedPart) setEdit(editFromPart(selectedPart));
        return next;
      });
    } catch (error) {
      reportError(error instanceof Error ? error.message : t("inventory.loadError"));
    } finally {
      setLoading(false);
    }
  }, [reportError, t]);

  useEffect(() => {
    void loadInventory();
  }, [loadInventory]);

  const selected = parts.find((part) => part.id === selectedId) ?? null;
  const selectedMovements = movements.filter((item) => item.part_id === selectedId).slice(0, 12);
  const filtered = useMemo(() => {
    const normalized = query.trim().toLocaleLowerCase(language === "tr" ? "tr-TR" : "en-US");
    return parts.filter((part) => {
      if (lowOnly && !part.is_low_stock) return false;
      if (!normalized) return true;
      return [part.sku, part.name, part.brand, part.category]
        .filter(Boolean)
        .some((value) => value!.toLocaleLowerCase().includes(normalized));
    });
  }, [language, lowOnly, parts, query]);

  function selectPart(part: InventoryPart) {
    setSelectedId(part.id);
    setEdit(editFromPart(part));
  }

  async function createPart(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    try {
      const created = await api.createInventoryPart({
        ...form,
        brand: form.brand.trim() || null,
        category: form.category.trim() || null,
      });
      setForm(emptyPart);
      setShowForm(false);
      setSelectedId(created.id);
      setEdit(editFromPart(created));
      notify(t("inventory.created"));
      await loadInventory();
    } catch (error) {
      reportError(error instanceof Error ? error.message : t("inventory.createError"));
    } finally {
      setSaving(false);
    }
  }

  async function savePart(event: FormEvent) {
    event.preventDefault();
    if (!selected || !edit) return;
    setSaving(true);
    try {
      await api.updateInventoryPart(selected.id, {
        ...edit,
        brand: edit.brand.trim() || null,
        category: edit.category.trim() || null,
      });
      notify(t("inventory.updated"));
      await loadInventory();
    } catch (error) {
      reportError(error instanceof Error ? error.message : t("inventory.updateError"));
    } finally {
      setSaving(false);
    }
  }

  async function saveMovement(event: FormEvent) {
    event.preventDefault();
    if (!selected) return;
    setSaving(true);
    try {
      await api.recordStockMovement(selected.id, {
        movement_type: movement.movement_type,
        quantity: movement.quantity,
        notes: movement.notes.trim() || null,
      });
      setMovement({ movement_type: "stock_in", quantity: "", notes: "" });
      notify(t("inventory.movementSaved"));
      await loadInventory();
    } catch (error) {
      reportError(error instanceof Error ? error.message : t("inventory.movementError"));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="page-stack">
      <section className="page-title-row">
        <div><span className="section-kicker">{t("inventory.kicker")}</span><h2>{t("inventory.title")}</h2><p>{t("inventory.subtitle")}</p></div>
        <button className="primary-button" onClick={() => setShowForm((value) => !value)}><Plus size={18} /> {t("inventory.addPart")}</button>
      </section>

      <section className="metric-grid inventory-metrics">
        <div className="metric-card"><span className="metric-icon blue"><Boxes size={22} /></span><div><strong>{summary?.total_parts ?? 0}</strong><span>{t("inventory.totalParts")}</span></div></div>
        <div className="metric-card"><span className="metric-icon orange"><AlertTriangle size={22} /></span><div><strong>{summary?.low_stock_parts ?? 0}</strong><span>{t("inventory.lowStock")}</span></div></div>
        <div className="metric-card"><span className="metric-icon purple"><PackageX size={22} /></span><div><strong>{summary?.out_of_stock_parts ?? 0}</strong><span>{t("inventory.outOfStock")}</span></div></div>
        <div className="metric-card"><span className="metric-icon green"><Coins size={22} /></span><div><strong>{formatCurrency(summary?.inventory_cost_value ?? 0, language)}</strong><span>{t("inventory.costValue")}</span></div></div>
      </section>

      {showForm && <section className="panel form-panel"><div className="panel-heading"><div><span className="section-kicker">{t("inventory.newRecord")}</span><h3>{t("inventory.partCard")}</h3></div></div><form className="inventory-form" onSubmit={createPart}>
        <label>{t("inventory.sku")}<input required minLength={2} value={form.sku} onChange={(event) => setForm({ ...form, sku: event.target.value.toUpperCase() })} placeholder="FLT-001" /></label>
        <label>{t("inventory.name")}<input required minLength={2} value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} placeholder={t("inventory.namePlaceholder")} /></label>
        <label>{t("inventory.brand")}<input value={form.brand} onChange={(event) => setForm({ ...form, brand: event.target.value })} /></label>
        <label>{t("inventory.category")}<input value={form.category} onChange={(event) => setForm({ ...form, category: event.target.value })} /></label>
        <label>{t("inventory.unit")}<select value={form.unit} onChange={(event) => setForm({ ...form, unit: event.target.value })}><option value="piece">{t("inventory.unit.piece")}</option><option value="liter">{t("inventory.unit.liter")}</option><option value="set">{t("inventory.unit.set")}</option></select></label>
        <label>{t("inventory.initialQuantity")}<input type="number" min="0" step="0.01" value={form.initial_quantity} onChange={(event) => setForm({ ...form, initial_quantity: event.target.value })} /></label>
        <label>{t("inventory.threshold")}<input type="number" min="0" step="0.01" value={form.low_stock_threshold} onChange={(event) => setForm({ ...form, low_stock_threshold: event.target.value })} /></label>
        <label>{t("inventory.purchasePrice")}<input type="number" min="0" step="0.01" value={form.purchase_price} onChange={(event) => setForm({ ...form, purchase_price: event.target.value })} /></label>
        <label>{t("inventory.salePrice")}<input type="number" min="0" step="0.01" value={form.sale_price} onChange={(event) => setForm({ ...form, sale_price: event.target.value })} /></label>
        <div className="form-actions"><button type="button" className="ghost-button" onClick={() => setShowForm(false)}>{t("common.cancel")}</button><button className="primary-button" disabled={saving}>{saving ? t("common.saving") : t("inventory.savePart")}</button></div>
      </form></section>}

      <section className="inventory-layout">
        <div className="panel">
          <div className="list-toolbar inventory-toolbar"><div><span className="section-kicker">{t("inventory.records", { count: parts.length })}</span><h3>{t("inventory.parts")}</h3></div><div className="inventory-filters"><label className="search-input"><Search size={17} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder={t("inventory.search")} /></label><label className="low-filter"><input type="checkbox" checked={lowOnly} onChange={(event) => setLowOnly(event.target.checked)} /> {t("inventory.lowOnly")}</label></div></div>
          {loading ? <div className="empty-state"><p>{t("inventory.loading")}</p></div> : <div className="parts-table">
            {filtered.map((part) => <button key={part.id} className={`part-row ${selectedId === part.id ? "selected" : ""} ${!part.active ? "inactive" : ""}`} onClick={() => selectPart(part)}><span className={`stock-indicator ${part.is_low_stock ? "low" : "ok"}`}><PackageCheck size={19} /></span><span className="part-main"><strong>{part.name}</strong><small>{part.sku} · {[part.brand, part.category].filter(Boolean).join(" · ") || "—"}</small></span><span className="part-stock"><strong>{part.stock_quantity} {t(`inventory.unit.${part.unit}`)}</strong><small>{part.is_low_stock ? t("inventory.lowBadge") : t("inventory.stockOk")}</small></span><span className="part-price">{formatCurrency(part.sale_price, language)}</span></button>)}
            {filtered.length === 0 && <div className="empty-state tall-empty"><Boxes size={32} /><p>{t("inventory.noParts")}</p></div>}
          </div>}
        </div>

        <aside className="panel inventory-detail">
          {!selected || !edit ? <div className="empty-state tall-empty"><Boxes size={32} /><p>{t("inventory.selectPart")}</p></div> : <>
            <div className="detail-head"><div><span className="section-kicker">{selected.sku}</span><h3>{selected.name}</h3></div><span className={`inventory-status ${selected.is_low_stock ? "low" : "ok"}`}>{selected.is_low_stock ? t("inventory.lowBadge") : t("inventory.stockOk")}</span></div>
            <div className="stock-hero"><small>{t("inventory.currentStock")}</small><strong>{selected.stock_quantity} {t(`inventory.unit.${selected.unit}`)}</strong><span>{t("inventory.threshold")}: {selected.low_stock_threshold}</span></div>

            <form className="movement-form" onSubmit={saveMovement}><div className="movement-toggle"><button type="button" className={movement.movement_type === "stock_in" ? "active" : ""} onClick={() => setMovement({ ...movement, movement_type: "stock_in" })}><ArrowDownToLine size={17} /> {t("inventory.stockIn")}</button><button type="button" className={movement.movement_type === "stock_out" ? "active danger" : ""} onClick={() => setMovement({ ...movement, movement_type: "stock_out" })}><ArrowUpFromLine size={17} /> {t("inventory.stockOut")}</button></div><label>{t("inventory.quantity")}<input required type="number" min="0.01" step="0.01" value={movement.quantity} onChange={(event) => setMovement({ ...movement, quantity: event.target.value })} /></label><label>{t("inventory.movementNote")}<input value={movement.notes} onChange={(event) => setMovement({ ...movement, notes: event.target.value })} placeholder={t("inventory.movementPlaceholder")} /></label><button className="primary-button full-button" disabled={saving}>{t("inventory.saveMovement")}</button></form>

            <details className="part-edit"><summary>{t("inventory.editPart")}</summary><form onSubmit={savePart}><label>{t("inventory.sku")}<input required value={edit.sku} onChange={(event) => setEdit({ ...edit, sku: event.target.value.toUpperCase() })} /></label><label>{t("inventory.name")}<input required value={edit.name} onChange={(event) => setEdit({ ...edit, name: event.target.value })} /></label><div className="edit-grid"><label>{t("inventory.brand")}<input value={edit.brand} onChange={(event) => setEdit({ ...edit, brand: event.target.value })} /></label><label>{t("inventory.category")}<input value={edit.category} onChange={(event) => setEdit({ ...edit, category: event.target.value })} /></label><label>{t("inventory.threshold")}<input type="number" min="0" step="0.01" value={edit.low_stock_threshold} onChange={(event) => setEdit({ ...edit, low_stock_threshold: event.target.value })} /></label><label>{t("inventory.purchasePrice")}<input type="number" min="0" step="0.01" value={edit.purchase_price} onChange={(event) => setEdit({ ...edit, purchase_price: event.target.value })} /></label><label>{t("inventory.salePrice")}<input type="number" min="0" step="0.01" value={edit.sale_price} onChange={(event) => setEdit({ ...edit, sale_price: event.target.value })} /></label><label>{t("inventory.unit")}<select value={edit.unit} onChange={(event) => setEdit({ ...edit, unit: event.target.value })}><option value="piece">{t("inventory.unit.piece")}</option><option value="liter">{t("inventory.unit.liter")}</option><option value="set">{t("inventory.unit.set")}</option></select></label></div><label className="check-label"><input type="checkbox" checked={edit.active} onChange={(event) => setEdit({ ...edit, active: event.target.checked })} /><span>{t("inventory.active")}<small>{t("inventory.activeHelp")}</small></span></label><button className="secondary-button full-button" disabled={saving}>{t("inventory.updatePart")}</button></form></details>

            <div className="stock-history"><strong>{t("inventory.history")}</strong>{selectedMovements.length === 0 ? <small>{t("inventory.noMovements")}</small> : selectedMovements.map((item) => <div key={item.id}><span className={Number(item.quantity_delta) >= 0 ? "positive" : "negative"}>{Number(item.quantity_delta) >= 0 ? "+" : ""}{item.quantity_delta}</span><span><strong>{t(`inventory.movement.${item.movement_type}`)}</strong><small>{formatDate(item.created_at, language)}{item.notes ? ` · ${item.notes}` : ""}</small></span><strong>{item.balance_after}</strong></div>)}</div>
          </>}
        </aside>
      </section>
    </div>
  );
}
