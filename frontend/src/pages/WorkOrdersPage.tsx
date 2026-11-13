import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  CalendarDays,
  CheckCircle2,
  ChevronRight,
  ClipboardList,
  Plus,
  Search,
  ShieldCheck,
  Wrench,
} from "lucide-react";

import { api } from "../api";
import { StatusBadge } from "../components/StatusBadge";
import type { Vehicle, WorkOrder, WorkOrderStatus } from "../types";
import { formatDate, orderCode, STATUS_OPTIONS } from "../utils";

export type IntakeDraft = {
  customer_complaint?: string;
  symptoms?: string;
  actions?: string;
  dtc_code?: string;
  voice_transcript?: string;
};

const emptyOrder = {
  vehicle_id: "",
  customer_complaint: "",
  symptoms: "",
  diagnosis: "",
  actions: "",
  result: "",
  dtc_code: "",
  voice_transcript: "",
  status: "inspection" as WorkOrderStatus,
  approved_by_mechanic: false,
};

type Props = {
  vehicles: Vehicle[];
  orders: WorkOrder[];
  initialDraft: IntakeDraft | null;
  onDraftConsumed: () => void;
  onChanged: () => Promise<void>;
  notify: (message: string) => void;
  reportError: (message: string) => void;
};

export function WorkOrdersPage({
  vehicles,
  orders,
  initialDraft,
  onDraftConsumed,
  onChanged,
  notify,
  reportError,
}: Props) {
  const [form, setForm] = useState(emptyOrder);
  const [showForm, setShowForm] = useState(orders.length === 0);
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<WorkOrderStatus | "all">("all");
  const [selectedId, setSelectedId] = useState<string | null>(orders[0]?.id ?? null);
  const [saving, setSaving] = useState(false);
  const [updatingId, setUpdatingId] = useState<string | null>(null);

  useEffect(() => {
    if (!initialDraft) return;
    setForm((current) => ({ ...current, ...initialDraft }));
    setShowForm(true);
    onDraftConsumed();
  }, [initialDraft, onDraftConsumed]);

  const vehicleMap = useMemo(() => new Map(vehicles.map((vehicle) => [vehicle.id, vehicle])), [vehicles]);
  const selectedOrder = orders.find((order) => order.id === selectedId) ?? orders[0] ?? null;

  const filteredOrders = useMemo(() => {
    const normalized = query.trim().toLocaleLowerCase("tr-TR");
    return orders.filter((order) => {
      if (statusFilter !== "all" && order.status !== statusFilter) return false;
      if (!normalized) return true;
      const vehicle = vehicleMap.get(order.vehicle_id);
      return [
        orderCode(order.id),
        order.customer_complaint,
        order.diagnosis,
        vehicle?.anonymous_code,
        vehicle?.brand,
        vehicle?.model,
        ...order.dtc_codes.map((item) => item.code),
      ].filter(Boolean).some((value) => value!.toLocaleLowerCase("tr-TR").includes(normalized));
    });
  }, [orders, query, statusFilter, vehicleMap]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    try {
      const dtcCodes = form.dtc_code
        .split(/[,;\s]+/)
        .map((code) => code.trim().toUpperCase())
        .filter(Boolean)
        .map((code) => ({ code }));
      const created = await api.createWorkOrder({
        vehicle_id: form.vehicle_id,
        customer_complaint: form.customer_complaint,
        symptoms: form.symptoms || null,
        diagnosis: form.diagnosis || null,
        actions: form.actions || null,
        result: form.result || null,
        status: form.status,
        approved_by_mechanic: form.approved_by_mechanic,
        voice_transcript: form.voice_transcript || null,
        dtc_codes: dtcCodes,
      });
      setForm(emptyOrder);
      setShowForm(false);
      setSelectedId(created.id);
      notify(`${orderCode(created.id)} numaralı iş emri oluşturuldu.`);
      await onChanged();
    } catch (error) {
      reportError(error instanceof Error ? error.message : "İş emri oluşturulamadı.");
    } finally {
      setSaving(false);
    }
  }

  async function updateOrder(id: string, payload: Record<string, unknown>, message: string) {
    setUpdatingId(id);
    try {
      await api.updateWorkOrder(id, payload);
      notify(message);
      await onChanged();
    } catch (error) {
      reportError(error instanceof Error ? error.message : "İş emri güncellenemedi.");
    } finally {
      setUpdatingId(null);
    }
  }

  return (
    <div className="page-stack">
      <section className="page-title-row">
        <div><span className="section-kicker">Servis operasyonu</span><h2>İş emirleri</h2><p>Arıza kabulünü, onarımı ve usta onayını tek kayıt üzerinden yönetin.</p></div>
        <button className="primary-button" onClick={() => setShowForm((value) => !value)}><Plus size={18} /> Yeni iş emri</button>
      </section>

      {showForm && (
        <section className="panel form-panel">
          <div className="panel-heading"><div><span className="section-kicker">Servis kabulü</span><h3>Yeni iş emri oluştur</h3></div></div>
          {vehicles.length === 0 ? (
            <div className="inline-warning">İş emri oluşturmadan önce bir araç kaydetmelisiniz.</div>
          ) : (
            <form className="form-grid order-form" onSubmit={submit}>
              <label>Araç<select required value={form.vehicle_id} onChange={(event) => setForm({ ...form, vehicle_id: event.target.value })}><option value="">Araç seçiniz</option>{vehicles.map((vehicle) => <option value={vehicle.id} key={vehicle.id}>{vehicle.anonymous_code} · {vehicle.brand} {vehicle.model}</option>)}</select></label>
              <label>Başlangıç durumu<select value={form.status} onChange={(event) => setForm({ ...form, status: event.target.value as WorkOrderStatus })}>{STATUS_OPTIONS.filter(([status]) => status !== "cancelled").map(([status, label]) => <option value={status} key={status}>{label}</option>)}</select></label>
              <label className="span-2">Müşteri şikâyeti<textarea required minLength={3} rows={3} value={form.customer_complaint} onChange={(event) => setForm({ ...form, customer_complaint: event.target.value })} placeholder="Araç düşük devirde çekişten düşüyor…" /></label>
              <label>Gözlenen belirtiler<textarea rows={3} value={form.symptoms} onChange={(event) => setForm({ ...form, symptoms: event.target.value })} placeholder="Duman, titreşim, ses…" /></label>
              <label>OBD-II kodları<input value={form.dtc_code} onChange={(event) => setForm({ ...form, dtc_code: event.target.value.toUpperCase() })} placeholder="P0299, P0401" /></label>
              <label>Kesinleşen arıza<textarea rows={3} value={form.diagnosis} onChange={(event) => setForm({ ...form, diagnosis: event.target.value })} placeholder="Kontrol sonrası doldurulabilir" /></label>
              <label>Yapılan işlemler<textarea rows={3} value={form.actions} onChange={(event) => setForm({ ...form, actions: event.target.value })} /></label>
              <label className="span-2">Sonuç ve notlar<textarea rows={2} value={form.result} onChange={(event) => setForm({ ...form, result: event.target.value })} /></label>
              <label className="check-label span-2"><input type="checkbox" checked={form.approved_by_mechanic} onChange={(event) => setForm({ ...form, approved_by_mechanic: event.target.checked })} /><span><strong>Usta tarafından doğrulandı</strong><small>Bu kayıt benzer vaka aramasında güvenilir örnek olarak kullanılabilir.</small></span></label>
              <div className="form-actions span-2"><button type="button" className="ghost-button" onClick={() => setShowForm(false)}>Vazgeç</button><button className="primary-button" disabled={saving}>{saving ? "Kaydediliyor…" : "İş emrini oluştur"}</button></div>
            </form>
          )}
        </section>
      )}

      <section className="orders-layout">
        <article className="panel order-list-panel">
          <div className="list-toolbar stacked-toolbar">
            <div><span className="section-kicker">{orders.length} kayıt</span><h3>Servis iş emirleri</h3></div>
            <div className="filter-row">
              <label className="search-input"><Search size={17} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Araç, şikâyet veya OBD kodu" /></label>
              <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value as WorkOrderStatus | "all")}><option value="all">Tüm durumlar</option>{STATUS_OPTIONS.map(([status, label]) => <option value={status} key={status}>{label}</option>)}</select>
            </div>
          </div>
          <div className="order-list">
            {filteredOrders.map((order) => {
              const vehicle = vehicleMap.get(order.vehicle_id);
              return (
                <button className={`order-row ${selectedOrder?.id === order.id ? "selected" : ""}`} key={order.id} onClick={() => setSelectedId(order.id)}>
                  <span className="order-row-icon"><Wrench size={18} /></span>
                  <span className="order-row-copy"><strong>{vehicle ? `${vehicle.brand} ${vehicle.model}` : "Bilinmeyen araç"}</strong><small>{orderCode(order.id)} · {order.customer_complaint}</small></span>
                  <StatusBadge status={order.status} />
                  <ChevronRight size={17} />
                </button>
              );
            })}
            {filteredOrders.length === 0 && <div className="empty-state"><ClipboardList size={30} /><p>Bu filtreye uygun iş emri bulunamadı.</p></div>}
          </div>
        </article>

        <aside className="panel order-detail">
          {selectedOrder ? (() => {
            const vehicle = vehicleMap.get(selectedOrder.vehicle_id);
            return (
              <>
                <div className="detail-head"><div><span className="section-kicker">{orderCode(selectedOrder.id)}</span><h3>{vehicle ? `${vehicle.brand} ${vehicle.model}` : "Araç kaydı"}</h3></div><StatusBadge status={selectedOrder.status} /></div>
                <div className="detail-meta"><span><CalendarDays size={15} /> {formatDate(selectedOrder.created_at)}</span><span><ShieldCheck size={15} /> {selectedOrder.approved_by_mechanic ? "Usta onaylı" : "Onay bekliyor"}</span></div>
                <div className="detail-block"><span>Müşteri şikâyeti</span><p>{selectedOrder.customer_complaint}</p></div>
                {selectedOrder.symptoms && <div className="detail-block"><span>Belirtiler</span><p>{selectedOrder.symptoms}</p></div>}
                {selectedOrder.diagnosis && <div className="detail-block"><span>Kesinleşen arıza</span><p>{selectedOrder.diagnosis}</p></div>}
                {selectedOrder.actions && <div className="detail-block"><span>Yapılan işlemler</span><p>{selectedOrder.actions}</p></div>}
                {selectedOrder.result && <div className="detail-block"><span>Sonuç</span><p>{selectedOrder.result}</p></div>}
                <div className="dtc-list">{selectedOrder.dtc_codes.map((item) => <span className="dtc-chip" title={item.description ?? undefined} key={item.code}>{item.code}</span>)}{selectedOrder.dtc_codes.length === 0 && <span className="muted-text">OBD kodu yok</span>}</div>
                <label className="detail-control">İş emri durumu<select disabled={updatingId === selectedOrder.id} value={selectedOrder.status} onChange={(event) => void updateOrder(selectedOrder.id, { status: event.target.value }, "İş emri durumu güncellendi.")}>{STATUS_OPTIONS.map(([status, label]) => <option value={status} key={status}>{label}</option>)}</select></label>
                {!selectedOrder.approved_by_mechanic && <button className="secondary-button full-button" disabled={updatingId === selectedOrder.id} onClick={() => void updateOrder(selectedOrder.id, { approved_by_mechanic: true }, "Kayıt usta onaylı vaka olarak işaretlendi.")}><CheckCircle2 size={17} /> Usta onayı ver</button>}
              </>
            );
          })() : <div className="empty-state"><ClipboardList size={30} /><p>Detayını görmek için bir iş emri seçin.</p></div>}
        </aside>
      </section>
    </div>
  );
}
