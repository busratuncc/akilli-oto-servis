import { FormEvent, useEffect, useMemo, useState } from "react";

import { api } from "./api";
import type { CaseSearchResult, ExtractionPreview, Vehicle, WorkOrder } from "./types";

const emptyVehicle = {
  anonymous_code: "",
  brand: "",
  model: "",
  model_year: "",
  engine: "",
  fuel_type: "",
  mileage: "",
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
};

function App() {
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [orders, setOrders] = useState<WorkOrder[]>([]);
  const [vehicleForm, setVehicleForm] = useState(emptyVehicle);
  const [orderForm, setOrderForm] = useState(emptyOrder);
  const [previewText, setPreviewText] = useState("");
  const [preview, setPreview] = useState<ExtractionPreview | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchCode, setSearchCode] = useState("");
  const [searchResults, setSearchResults] = useState<CaseSearchResult[]>([]);
  const [message, setMessage] = useState("Sistem hazırlanıyor...");
  const [error, setError] = useState("");

  const vehicleMap = useMemo(
    () => new Map(vehicles.map((vehicle) => [vehicle.id, vehicle])),
    [vehicles],
  );

  async function refresh() {
    try {
      const [vehicleData, orderData, health] = await Promise.all([
        api.listVehicles(),
        api.listWorkOrders(),
        api.health(),
      ]);
      setVehicles(vehicleData);
      setOrders(orderData);
      setMessage(`${health.service} çalışıyor`);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Bağlantı kurulamadı");
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  async function submitVehicle(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      await api.createVehicle({
        ...vehicleForm,
        model_year: vehicleForm.model_year ? Number(vehicleForm.model_year) : null,
        mileage: vehicleForm.mileage ? Number(vehicleForm.mileage) : null,
      });
      setVehicleForm(emptyVehicle);
      setMessage("Araç kaydedildi");
      await refresh();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Araç kaydedilemedi");
    }
  }

  async function submitOrder(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      await api.createWorkOrder({
        vehicle_id: orderForm.vehicle_id,
        customer_complaint: orderForm.customer_complaint,
        symptoms: orderForm.symptoms || null,
        diagnosis: orderForm.diagnosis || null,
        actions: orderForm.actions || null,
        result: orderForm.result || null,
        status: "confirmed",
        approved_by_mechanic: true,
        voice_transcript: orderForm.voice_transcript || null,
        dtc_codes: orderForm.dtc_code ? [{ code: orderForm.dtc_code }] : [],
      });
      setOrderForm(emptyOrder);
      setMessage("Servis kaydı oluşturuldu");
      await refresh();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Servis kaydı oluşturulamadı");
    }
  }

  async function createPreview(event: FormEvent) {
    event.preventDefault();
    try {
      const result = await api.extractionPreview(previewText);
      setPreview(result);
      setOrderForm((current) => ({
        ...current,
        customer_complaint: previewText,
        voice_transcript: previewText,
        dtc_code: result.dtc_codes[0] ?? current.dtc_code,
      }));
      setMessage("Ön izleme hazır; kaydetmeden önce usta kontrolü gerekir");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Ön izleme oluşturulamadı");
    }
  }

  async function searchCases(event: FormEvent) {
    event.preventDefault();
    try {
      setSearchResults(await api.searchCases(searchQuery, searchCode));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Arama yapılamadı");
    }
  }

  return (
    <main>
      <header className="hero">
        <div>
          <p className="eyebrow">Tez projesi · geliştirme temeli</p>
          <h1>Akıllı Oto Servis</h1>
          <p className="hero-copy">
            Doğrulanmış servis hafızası, OBD-II kayıtları ve kanıta dayalı karar desteği için başlangıç uygulaması.
          </p>
        </div>
        <div className="status"><span />{message}</div>
      </header>

      {error && <div className="alert">{error}</div>}

      <section className="stats">
        <article><strong>{vehicles.length}</strong><span>Araç</span></article>
        <article><strong>{orders.length}</strong><span>Servis kaydı</span></article>
        <article><strong>{orders.filter((item) => item.approved_by_mechanic).length}</strong><span>Usta onaylı vaka</span></article>
      </section>

      <section className="grid two-columns">
        <article className="card">
          <h2>1. Araç ekle</h2>
          <p className="muted">Müşteri bilgisi yerine anonim araç kodu kullanın.</p>
          <form onSubmit={submitVehicle} className="form-grid">
            <label>Anonim kod<input required value={vehicleForm.anonymous_code} onChange={(e) => setVehicleForm({ ...vehicleForm, anonymous_code: e.target.value })} placeholder="ARAC-001" /></label>
            <label>Marka<input required value={vehicleForm.brand} onChange={(e) => setVehicleForm({ ...vehicleForm, brand: e.target.value })} placeholder="Renault" /></label>
            <label>Model<input required value={vehicleForm.model} onChange={(e) => setVehicleForm({ ...vehicleForm, model: e.target.value })} placeholder="Clio" /></label>
            <label>Model yılı<input type="number" value={vehicleForm.model_year} onChange={(e) => setVehicleForm({ ...vehicleForm, model_year: e.target.value })} placeholder="2015" /></label>
            <label>Motor<input value={vehicleForm.engine} onChange={(e) => setVehicleForm({ ...vehicleForm, engine: e.target.value })} placeholder="1.5 dCi" /></label>
            <label>Kilometre<input type="number" value={vehicleForm.mileage} onChange={(e) => setVehicleForm({ ...vehicleForm, mileage: e.target.value })} placeholder="182000" /></label>
            <button type="submit">Aracı kaydet</button>
          </form>
        </article>

        <article className="card accent-card">
          <h2>2. Anlatımı yapılandır</h2>
          <p className="muted">Şimdilik metin ve kural motoru kullanılır; ses/LLM modülü sonraki iterasyonda bağlanacak.</p>
          <form onSubmit={createPreview}>
            <label>Ustanın anlatımı<textarea required rows={7} value={previewText} onChange={(e) => setPreviewText(e.target.value)} placeholder="Araç 182 bin kilometrede, çekişten düşüyor ve P0299 kodu verdi..." /></label>
            <button type="submit">Ön izleme oluştur</button>
          </form>
          {preview && (
            <div className="preview">
              <div><span>OBD kodları</span><strong>{preview.dtc_codes.join(", ") || "Bulunamadı"}</strong></div>
              <div><span>Kilometre</span><strong>{preview.mileage?.toLocaleString("tr-TR") ?? "Bulunamadı"}</strong></div>
              <small>{preview.warnings.join(" ")}</small>
            </div>
          )}
        </article>
      </section>

      <section className="card full-card">
        <h2>3. Usta onaylı servis kaydı</h2>
        <form onSubmit={submitOrder} className="form-grid order-grid">
          <label>Araç<select required value={orderForm.vehicle_id} onChange={(e) => setOrderForm({ ...orderForm, vehicle_id: e.target.value })}><option value="">Araç seçin</option>{vehicles.map((vehicle) => <option key={vehicle.id} value={vehicle.id}>{vehicle.anonymous_code} · {vehicle.brand} {vehicle.model}</option>)}</select></label>
          <label>OBD-II kodu<input value={orderForm.dtc_code} onChange={(e) => setOrderForm({ ...orderForm, dtc_code: e.target.value.toUpperCase() })} placeholder="P0299" maxLength={5} /></label>
          <label className="wide">Müşteri şikâyeti<textarea required rows={3} value={orderForm.customer_complaint} onChange={(e) => setOrderForm({ ...orderForm, customer_complaint: e.target.value })} /></label>
          <label>Belirtiler<textarea rows={3} value={orderForm.symptoms} onChange={(e) => setOrderForm({ ...orderForm, symptoms: e.target.value })} /></label>
          <label>Kesinleşen arıza<textarea rows={3} value={orderForm.diagnosis} onChange={(e) => setOrderForm({ ...orderForm, diagnosis: e.target.value })} /></label>
          <label>Yapılan işlem<textarea rows={3} value={orderForm.actions} onChange={(e) => setOrderForm({ ...orderForm, actions: e.target.value })} /></label>
          <label>Sonuç<textarea rows={3} value={orderForm.result} onChange={(e) => setOrderForm({ ...orderForm, result: e.target.value })} /></label>
          <button type="submit">Onaylı vaka olarak kaydet</button>
        </form>
      </section>

      <section className="grid two-columns">
        <article className="card">
          <h2>4. Benzer vaka ara</h2>
          <form onSubmit={searchCases} className="search-form">
            <input required value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} placeholder="çekiş düşüklüğü turbo" />
            <input value={searchCode} onChange={(e) => setSearchCode(e.target.value.toUpperCase())} placeholder="P0299" maxLength={5} />
            <button type="submit">Ara</button>
          </form>
          <div className="result-list">
            {searchResults.map((result) => (
              <div key={result.work_order.id} className="result-item">
                <strong>{result.vehicle.brand} {result.vehicle.model}</strong>
                <span>{result.work_order.customer_complaint}</span>
                <small>{result.match_reason}</small>
              </div>
            ))}
            {searchResults.length === 0 && <p className="muted">Henüz arama sonucu yok.</p>}
          </div>
        </article>

        <article className="card">
          <h2>Son servis kayıtları</h2>
          <div className="result-list">
            {orders.slice(0, 6).map((order) => {
              const vehicle = vehicleMap.get(order.vehicle_id);
              return (
                <div key={order.id} className="result-item">
                  <strong>{vehicle ? `${vehicle.brand} ${vehicle.model}` : "Bilinmeyen araç"}</strong>
                  <span>{order.customer_complaint}</span>
                  <small>{order.dtc_codes.map((item) => item.code).join(", ") || "OBD kodu yok"} · {order.status}</small>
                </div>
              );
            })}
            {orders.length === 0 && <p className="muted">İlk servis kaydını oluşturun.</p>}
          </div>
        </article>
      </section>
    </main>
  );
}

export default App;

