import { NavLink, Outlet } from "react-router-dom";

import PeriodPicker from "./PeriodPicker";

const MENU = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/matches", label: "Mecze" },
  { to: "/referees", label: "Sędziowie" },
  { to: "/availability", label: "Dyspozycyjność" },
  { to: "/assignments", label: "Obsada" },
  { to: "/venues", label: "Obiekty" },
  { to: "/settings", label: "Ustawienia" },
];

export default function Layout() {
  return (
    <div className="flex min-h-screen flex-col md:flex-row">
      <aside className="bg-emerald-900 text-emerald-50 md:w-56 md:shrink-0">
        <div className="px-5 py-4 text-xl font-bold tracking-tight">
          Obsada<span className="text-emerald-300">+</span>
        </div>
        <nav className="flex gap-1 overflow-x-auto px-2 pb-2 md:flex-col md:pb-0">
          {MENU.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `whitespace-nowrap rounded-md px-3 py-2 text-sm font-medium ${
                  isActive ? "bg-emerald-700 text-white" : "text-emerald-100 hover:bg-emerald-800"
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 bg-white px-4 py-3 md:px-6">
          <span className="text-sm text-slate-500">Panel obsady sędziowskiej</span>
          <PeriodPicker />
        </header>
        <main className="flex-1 p-4 md:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
