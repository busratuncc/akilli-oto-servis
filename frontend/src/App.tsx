import { useCallback, useEffect, useMemo, useState } from "react";
import { CheckCircle2, Languages, LogOut, Moon, RefreshCw, Server, Sun, X } from "lucide-react";
import { Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";

import { api, ApiError } from "./api";
import { Sidebar } from "./components/Sidebar";
import { useI18n } from "./i18n";
import { AssistantPage } from "./pages/AssistantPage";
import { DashboardPage } from "./pages/DashboardPage";
import { LoginPage } from "./pages/LoginPage";
import { FinancePage } from "./pages/FinancePage";
import { CardPaymentPage } from "./pages/CardPaymentPage";
import { InventoryPage } from "./pages/InventoryPage";
import { TestBank3DPage } from "./pages/TestBank3DPage";
import { SettingsPage } from "./pages/SettingsPage";
import type { IntakeDraft } from "./pages/WorkOrdersPage";
import { WorkOrdersPage } from "./pages/WorkOrdersPage";
import { VehiclesPage } from "./pages/VehiclesPage";
import { useTheme } from "./theme";
import type { AuthUser, DashboardSummary, Vehicle, WorkOrder } from "./types";

const PAGE_TITLE_KEYS: Record<string, string> = {
  "/": "nav.dashboard",
  "/vehicles": "nav.vehicles",
  "/work-orders": "nav.orders",
  "/inventory": "nav.inventory",
  "/finance": "nav.finance",
  "/assistant": "nav.assistant",
  "/settings": "nav.settings",
};

function App() {
  const location = useLocation();
  const navigate = useNavigate();
  const { language, setLanguage, t } = useI18n();
  const { theme, toggleTheme } = useTheme();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [authLoading, setAuthLoading] = useState(true);
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
      if (requestError instanceof ApiError && requestError.status === 401) {
        setUser(null);
      } else {
        setError(requestError instanceof Error ? requestError.message : t("common.connectionError"));
      }
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    let active = true;
    void api.me()
      .then((result) => {
        if (!active) return;
        setUser(result.user);
        setLanguage(result.user.preferred_language);
      })
      .catch(() => {
        if (active) setUser(null);
      })
      .finally(() => {
        if (active) setAuthLoading(false);
      });
    return () => { active = false; };
  }, [setLanguage]);

  useEffect(() => {
    if (user) void refresh();
  }, [refresh, user?.id]);

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

  async function changeLanguage(next: "tr" | "en") {
    setLanguage(next);
    if (!user) return;
    try {
      const result = await api.updatePreferences(next);
      setUser(result.user);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : t("common.connectionError"));
    }
  }

  async function logout() {
    try {
      await api.logout();
    } finally {
      setUser(null);
      setVehicles([]);
      setOrders([]);
      setSummary(null);
      setHealthy(false);
      navigate("/");
    }
  }

  if (authLoading) {
    return <div className="auth-splash"><span className="splash-mark"><Server size={24} /></span><strong>{t("app.name")}</strong></div>;
  }

  if (!user) {
    return <LoginPage onAuthenticated={(authenticatedUser) => { setUser(authenticatedUser); setLanguage(authenticatedUser.preferred_language); }} />;
  }

  if (location.pathname === "/test-bank/3d") {
    return <TestBank3DPage />;
  }

  return (
    <div className="app-shell">
      <Sidebar />
      <div className="workspace">
        <header className="topbar">
          <div>
            <span className="breadcrumb">{t("app.name")} /</span>
            <strong>{t(PAGE_TITLE_KEYS[location.pathname] ?? "common.app")}</strong>
          </div>
          <div className="topbar-actions">
            <span className={`server-pill ${healthy ? "online" : "offline"}`}><Server size={15} /> {healthy ? t("common.online") : t("common.offline")}</span>
            <label className="compact-select" title={t("common.language")}><Languages size={16} /><select value={language} onChange={(event) => void changeLanguage(event.target.value as "tr" | "en")}><option value="tr">TR</option><option value="en">EN</option></select></label>
            <button className="icon-button" title={theme === "dark" ? t("common.light") : t("common.dark")} onClick={toggleTheme}>{theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}</button>
            <button className="icon-button" title={t("common.refresh")} onClick={() => void refresh()} disabled={loading}><RefreshCw size={18} className={loading ? "spin" : ""} /></button>
            <button className="user-button" title={`${user.full_name} · ${user.email}`} onClick={() => void logout()}><span>{user.full_name.split(" ")[0]}</span><LogOut size={17} /><span className="sr-only">{t("common.logout")}</span></button>
          </div>
        </header>

        <main className="page-content">
          {error && <div className="toast error-toast"><X size={18} /><span>{error}</span><button onClick={() => setError("")}><X size={16} /></button></div>}
          {notice && <div className="toast success-toast"><CheckCircle2 size={18} /><span>{notice}</span><button onClick={() => setNotice("")}><X size={16} /></button></div>}

          <Routes>
            <Route path="/" element={<DashboardPage summary={summary} vehicleMap={vehicleMap} />} />
            <Route path="/vehicles" element={<VehiclesPage vehicles={vehicles} orders={orders} onChanged={refresh} notify={setNotice} reportError={setError} />} />
            <Route path="/work-orders" element={<WorkOrdersPage vehicles={vehicles} orders={orders} initialDraft={intakeDraft} onDraftConsumed={consumeDraft} onChanged={refresh} notify={setNotice} reportError={setError} />} />
            <Route path="/inventory" element={<InventoryPage notify={setNotice} reportError={setError} />} />
            <Route path="/finance" element={<FinancePage vehicles={vehicles} orders={orders} notify={setNotice} reportError={setError} />} />
            <Route path="/finance/card-payment/:invoiceId" element={<CardPaymentPage reportError={setError} />} />
            <Route path="/assistant" element={<AssistantPage onUseDraft={useAssistantDraft} notify={setNotice} reportError={setError} />} />
            <Route path="/settings" element={<SettingsPage user={user} onUserUpdated={setUser} notify={setNotice} reportError={setError} />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}

export default App;
