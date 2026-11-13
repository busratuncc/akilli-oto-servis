import { FormEvent, useMemo, useState } from "react";
import { CarFront, Fuel, Gauge, Plus, Search } from "lucide-react";

import { api } from "../api";
import type { Vehicle, WorkOrder } from "../types";
import { formatNumber } from "../utils";

const emptyVehicle = {
  anonymous_code: "",
  brand: "",
  model: "",
  model_year: "",
  engine: "",
  fuel_type: "",
  mileage: "",
};

type Props = {
  vehicles: Vehicle[];
  orders: WorkOrder[];
  onChanged: () => Promise<void>;
  notify: (message: string) => void;
  reportError: (message: string) => void;
};

export function VehiclesPage({ vehicles, orders, onChanged, notify, reportError }: Props) {
  const [form, setForm] = useState(emptyVehicle);
  const [query, setQuery] = useState("");
  const [showForm, setShowForm] = useState(vehicles.length === 0);
  const [saving, setSaving] = useState(false);

  const filteredVehicles = useMemo(() => {
    const normalized = query.trim().toLocaleLowerCase("tr-TR");
    if (!normalized) return vehicles;
    return vehicles.filter((vehicle) =>
      [vehicle.anonymous_code, vehicle.brand, vehicle.model, vehicle.engine]
        .filter(Boolean)
        .some((value) => value!.toLocaleLowerCase("tr-TR").includes(normalized)),
    );
  }, [query, vehicles]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    try {
      await api.createVehicle({
        ...form,
        model_year: form.model_year ? Number(form.model_year) : null,
        mileage: form.mileage ? Number(form.mileage) : null,
      });
      setForm(emptyVehicle);
      setShowForm(false);
      notify("Araç başarıyla kaydedildi.");
      await onChanged();
    } catch (error) {
      reportError(error instanceof Error ? error.message : "Araç kaydedilemedi.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="page-stack">
      <section className="page-title-row">
        <div><span className="section-kicker">Araç yönetimi</span><h2>Kayıtlı araçlar</h2><p>Gerçek plaka yerine anonim kodla güvenli servis geçmişi oluşturun.</p></div>
        <button className="primary-button" onClick={() => setShowForm((value) => !value)}><Plus size={18} /> Araç ekle</button>
      </section>

      {showForm && (
        <section className="panel form-panel">
          <div className="panel-heading"><div><span className="section-kicker">Yeni kayıt</span><h3>Araç bilgileri</h3></div></div>
          <form className="form-grid" onSubmit={submit}>
            <label>Anonim araç kodu<input required minLength={3} value={form.anonymous_code} onChange={(event) => setForm({ ...form, anonymous_code: event.target.value.toUpperCase() })} placeholder="ARAC-001" /></label>
            <label>Marka<input required value={form.brand} onChange={(event) => setForm({ ...form, brand: event.target.value })} placeholder="Renault" /></label>
            <label>Model<input required value={form.model} onChange={(event) => setForm({ ...form, model: event.target.value })} placeholder="Clio" /></label>
            <label>Model yılı<input type="number" min="1950" max="2100" value={form.model_year} onChange={(event) => setForm({ ...form, model_year: event.target.value })} placeholder="2018" /></label>
            <label>Motor<input value={form.engine} onChange={(event) => setForm({ ...form, engine: event.target.value })} placeholder="1.5 dCi" /></label>
            <label>Yakıt tipi<select value={form.fuel_type} onChange={(event) => setForm({ ...form, fuel_type: event.target.value })}><option value="">Seçiniz</option><option>Dizel</option><option>Benzin</option><option>LPG</option><option>Hibrit</option><option>Elektrik</option></select></label>
            <label>Kilometre<input type="number" min="0" value={form.mileage} onChange={(event) => setForm({ ...form, mileage: event.target.value })} placeholder="182000" /></label>
            <div className="form-actions"><button type="button" className="ghost-button" onClick={() => setShowForm(false)}>Vazgeç</button><button className="primary-button" disabled={saving}>{saving ? "Kaydediliyor…" : "Aracı kaydet"}</button></div>
          </form>
        </section>
      )}

      <section className="panel">
        <div className="list-toolbar">
          <div><span className="section-kicker">{vehicles.length} kayıt</span><h3>Araç envanteri</h3></div>
          <label className="search-input"><Search size={17} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Kod, marka veya model ara" /></label>
        </div>

        <div className="vehicle-grid">
          {filteredVehicles.map((vehicle) => {
            const serviceCount = orders.filter((order) => order.vehicle_id === vehicle.id).length;
            return (
              <article className="vehicle-card" key={vehicle.id}>
                <div className="vehicle-card-head"><span className="vehicle-icon"><CarFront size={24} /></span><span className="code-chip">{vehicle.anonymous_code}</span></div>
                <h3>{vehicle.brand} {vehicle.model}</h3>
                <p>{vehicle.model_year ?? "Yıl belirtilmedi"} · {vehicle.engine || "Motor belirtilmedi"}</p>
                <div className="vehicle-meta"><span><Gauge size={15} /> {formatNumber(vehicle.mileage)} km</span><span><Fuel size={15} /> {vehicle.fuel_type || "—"}</span></div>
                <div className="vehicle-footer"><strong>{serviceCount}</strong><span>servis kaydı</span></div>
              </article>
            );
          })}
          {filteredVehicles.length === 0 && <div className="empty-state wide-empty"><CarFront size={30} /><p>Aramanızla eşleşen araç bulunamadı.</p></div>}
        </div>
      </section>
    </div>
  );
}
