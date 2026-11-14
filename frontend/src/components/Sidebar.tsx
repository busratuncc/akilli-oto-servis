import {
  Bot,
  CarFront,
  ClipboardList,
  Gauge,
  ReceiptText,
  Settings,
  ShieldCheck,
  Wrench,
  Warehouse,
  FlaskConical,
} from "lucide-react";
import { NavLink } from "react-router-dom";
import { useI18n } from "../i18n";

const links = [
  { to: "/", label: "nav.dashboard", icon: Gauge, end: true },
  { to: "/vehicles", label: "nav.vehicles", icon: CarFront },
  { to: "/work-orders", label: "nav.orders", icon: ClipboardList },
  { to: "/inventory", label: "nav.inventory", icon: Warehouse },
  { to: "/finance", label: "nav.finance", icon: ReceiptText },
  { to: "/assistant", label: "nav.assistant", icon: Bot },
  { to: "/evaluation", label: "nav.evaluation", icon: FlaskConical },
  { to: "/settings", label: "nav.settings", icon: Settings },
];

export function Sidebar() {
  const { t } = useI18n();
  return (
    <aside className="sidebar">
      <div className="brand">
        <span className="brand-mark"><Wrench size={22} /></span>
        <div>
          <strong>{t("app.name")}</strong>
          <small>{t("app.workshop")}</small>
        </div>
      </div>

      <nav className="navigation" aria-label={t("nav.menu")}>
        {links.map(({ to, label, icon: Icon, end }) => (
          <NavLink key={to} to={to} end={end} className={({ isActive }) => isActive ? "nav-link active" : "nav-link"}>
            <Icon size={19} />
            <span>{t(label)}</span>
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-footer">
        <ShieldCheck size={17} />
        <span>{t("app.prototype")}</span>
      </div>
    </aside>
  );
}
