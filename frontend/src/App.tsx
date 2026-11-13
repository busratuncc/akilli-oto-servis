import { useCallback, useEffect, useMemo, useState } from "react";
import { Bell, CheckCircle2, RefreshCw, Server, X } from "lucide-react";
import { Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";

import { api } from "./api";
import { Sidebar } from "./components/Sidebar";
import { AssistantPage } from "./pages/AssistantPage";
import { DashboardPage } from "./pages/DashboardPage";
import type { IntakeDraft } from "./pages/WorkOrdersPage";
import { WorkOrdersPage } from "./pages/WorkOrdersPage";
import { VehiclesPage } from "./pages/VehiclesPage";
import type { DashboardSummary, Vehicle, WorkOrder } from "./types";

const PAGE_TITLES: Record<string, string> = {
  "/": "Gösterge paneli",
  "/vehicles": "Araçlar",
  "/work-orders": "İş emirleri",
  "/assistant": "Akıllı asistan",
};

function App() {
  const location = useLocation();
  const navigate = useNavigate();
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [orders, setOrders] = useState<WorkOrder[]>([]);
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [healthy, setHealthy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [intakeDraft, setIntakeDraft] = useState<IntakeDraft | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [vehicleData, orderData, dashboardData, health] = await Promise.all([
        api.listVehicles(),
        api.listWorkOrders(),
        api.dashboard(),
        api.health(),
      ]);
      setVehicles(vehicleData);
      setOrders(orderData);
      setSummary(dashboardData);
      setHealthy(health.status === "ok");
      setError("");
    } catch (requestError) {
      setHealthy(false);
      setError(requestError instanceof Error ? requestError.message : "Sunucu bağlantısı kurulamadı.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    if (!notice) return;
    const timeout = window.setTimeout(() => setNotice(""), 4000);
    return () => window.clearTimeout(timeout);
  }, [notice]);

  const vehicleMap = useMemo(
    () => new Map(vehicles.map((vehicle) => [vehicle.id, vehicle])),
    [vehicles],
  );

  const consumeDraft = useCallback(() => setIntakeDraft(null), []);

  function useAssistantDraft(draft: IntakeDraft) {
    setIntakeDraft(draft);
    navigate("/work-orders");
  }

  return (
    <div className="app-shell">
      <Sidebar />
      <div className="workspace">
        <header className="topbar">
          <div>
            <span className="breadcrumb">Akıllı Oto Servis /</span>
            <strong>{PAGE_TITLES[location.pathname] ?? "Uygulama"}</strong>
          </div>
          <div className="topbar-actions">
            <span className={`server-pill ${healthy ? "online" : "offline"}`}><Server size={15} /> {healthy ? "Sistem çevrimiçi" : "Bağlantı yok"}</span>
            <button className="icon-button" title="Verileri yenile" onClick={() => void refresh()} disabled={loading}><RefreshCw size={18} className={loading ? "spin" : ""} /></button>
            <button className="icon-button" title="Bildirimler"><Bell size={18} /></button>
          </div>
        </header>

        <main className="page-content">
          {error && <div className="toast error-toast"><X size={18} /><span>{error}</span><button onClick={() => setError("")}><X size={16} /></button></div>}
          {notice && <div className="toast success-toast"><CheckCircle2 size={18} /><span>{notice}</span><button onClick={() => setNotice("")}><X size={16} /></button></div>}

          <Routes>
            <Route path="/" element={<DashboardPage summary={summary} vehicleMap={vehicleMap} />} />
            <Route path="/vehicles" element={<VehiclesPage vehicles={vehicles} orders={orders} onChanged={refresh} notify={setNotice} reportError={setError} />} />
            <Route path="/work-orders" element={<WorkOrdersPage vehicles={vehicles} orders={orders} initialDraft={intakeDraft} onDraftConsumed={consumeDraft} onChanged={refresh} notify={setNotice} reportError={setError} />} />
            <Route path="/assistant" element={<AssistantPage onUseDraft={useAssistantDraft} notify={setNotice} reportError={setError} />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}

export default App;
