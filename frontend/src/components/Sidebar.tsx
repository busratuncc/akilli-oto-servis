import {
  Bot,
  CarFront,
  ClipboardList,
  Gauge,
  Settings,
  Wrench,
} from "lucide-react";
import { NavLink } from "react-router-dom";

const links = [
  { to: "/", label: "Gösterge paneli", icon: Gauge, end: true },
  { to: "/vehicles", label: "Araçlar", icon: CarFront },
  { to: "/work-orders", label: "İş emirleri", icon: ClipboardList },
  { to: "/assistant", label: "Akıllı asistan", icon: Bot },
];

export function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="brand">
        <span className="brand-mark"><Wrench size={22} /></span>
        <div>
          <strong>Akıllı Servis</strong>
          <small>Atölye yönetimi</small>
        </div>
      </div>

      <nav className="navigation" aria-label="Ana menü">
        {links.map(({ to, label, icon: Icon, end }) => (
          <NavLink key={to} to={to} end={end} className={({ isActive }) => isActive ? "nav-link active" : "nav-link"}>
            <Icon size={19} />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-footer">
        <Settings size={17} />
        <span>Tez prototipi · v0.2</span>
      </div>
    </aside>
  );
}
