import { CalendarCheck, CalendarDays, ClipboardList, LayoutDashboard, MapPin, Settings, Users, type LucideIcon } from "lucide-react";
import { NavLink, Outlet, useLocation } from "react-router-dom";

import PeriodPicker from "./PeriodPicker";

interface MenuItem {
  to: string;
  label: string;
  icon: LucideIcon;
  end?: boolean;
}

const MENU: MenuItem[] = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/matches", label: "Mecze", icon: CalendarDays },
  { to: "/referees", label: "Sędziowie", icon: Users },
  { to: "/availability", label: "Dyspozycyjność", icon: CalendarCheck },
  { to: "/assignments", label: "Obsada", icon: ClipboardList },
  { to: "/venues", label: "Obiekty", icon: MapPin },
  { to: "/settings", label: "Ustawienia", icon: Settings },
];

function Logo() {
  return (
    <div className="flex items-center gap-2.5 px-2">
      <div className="flex size-9 items-center justify-center rounded-xl bg-gradient-to-br from-brand-500 to-violet-500 text-lg font-bold text-white shadow-md shadow-brand-500/30">
        +
      </div>
      <div className="leading-tight">
        <div className="text-[15px] font-semibold tracking-tight">Obsada+</div>
        <div className="text-[11px] text-zinc-500">Obsada sędziowska</div>
      </div>
    </div>
  );
}

export default function Layout() {
  const location = useLocation();
  return (
    <div className="flex min-h-screen flex-col lg:flex-row">
      <aside className="border-zinc-200/70 bg-white/80 backdrop-blur lg:sticky lg:top-0 lg:h-screen lg:w-64 lg:shrink-0 lg:border-r">
        <div className="flex items-center justify-between px-4 py-4 lg:block lg:px-4 lg:py-6">
          <Logo />
        </div>
        <nav className="flex gap-1 overflow-x-auto px-3 pb-3 lg:flex-col lg:px-3 lg:pb-0">
          <div className="hidden px-3 pb-2 text-[11px] font-semibold tracking-wider text-zinc-400 uppercase lg:block">Menu</div>
          {MENU.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `group flex items-center gap-3 rounded-xl px-3 py-2 text-sm font-medium whitespace-nowrap transition ${
                  isActive ? "bg-brand-50 text-brand-700" : "text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900"
                }`
              }
            >
              {({ isActive }) => (
                <>
                  <Icon className={`size-[18px] ${isActive ? "text-brand-600" : "text-zinc-400 group-hover:text-zinc-600"}`} strokeWidth={2} />
                  {label}
                </>
              )}
            </NavLink>
          ))}
        </nav>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex flex-wrap items-center justify-end gap-3 border-b border-zinc-200/70 bg-zinc-50/80 px-4 py-3 backdrop-blur md:px-8">
          <PeriodPicker />
        </header>
        <main key={location.pathname} className="animate-fade-in mx-auto w-full max-w-7xl flex-1 px-4 py-6 md:px-8 md:py-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
