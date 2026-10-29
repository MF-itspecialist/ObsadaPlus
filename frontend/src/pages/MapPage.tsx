import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { Car, Home } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { EmptyState, ErrorBanner, Loading, PageHeader } from "../components/Feedback";
import { SearchBox, matchesText } from "../components/Filters";
import { usePeriod } from "../context/PeriodContext";
import { useAsync } from "../hooks/useAsync";
import { api } from "../services/api";
import type { LatLng, MapReferee, MapVenue, PeriodMap } from "../types";
import { ROLE_LABELS } from "../types";
import { saturdayOf, shortDay } from "../utils/dates";

// Kolory jak w całej aplikacji: obsadzony / częściowo / brak obsady.
const FILL = { full: "#059669", partial: "#d97706", none: "#dc2626" };
// Kolejne dni trasy sędziego.
const DAY_COLORS = ["#4f46e5", "#0891b2", "#c026d3", "#ea580c"];
const WARSAW: LatLng = [52.23, 21.01];

function venueFill(v: MapVenue, day: string | null): string {
  const ms = v.matches.filter((m) => !day || m.date === day);
  if (ms.every((m) => m.filled >= m.required)) return FILL.full;
  if (ms.some((m) => m.filled > 0)) return FILL.partial;
  return FILL.none;
}

function esc(s: string): string {
  return s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]!);
}

function badge(text: string, color: string): L.DivIcon {
  return L.divIcon({
    className: "",
    html: `<div style="background:${color}" class="grid size-6 place-items-center rounded-full border-2 border-white text-[11px] font-bold text-white shadow">${text}</div>`,
    iconSize: [24, 24],
    iconAnchor: [12, 12],
  });
}

const HOME_ICON = L.divIcon({
  className: "",
  html: `<div class="grid size-7 place-items-center rounded-lg border-2 border-white bg-zinc-900 text-white shadow"><svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M3 10.5 12 3l9 7.5V21H3z"/></svg></div>`,
  iconSize: [28, 28],
  iconAnchor: [14, 14],
});

/** Mapa okresu: obiekty z meczami (kolor = stan obsady) i trasy wybranego sędziego. */
export default function MapPage() {
  const { period, setSaturday } = usePeriod();
  const data = useAsync(() => api.periodMap(period), [period.date_from, period.date_to]);
  const [params, setParams] = useSearchParams();
  const selected = params.get("referee") ? Number(params.get("referee")) : null;
  const day = params.get("date");
  const [query, setQuery] = useState("");

  // Link z innej strony (np. ze statystyk) z dniem spoza bieżącego weekendu.
  useEffect(() => {
    if (day && (day < period.date_from || day > period.date_to)) setSaturday(saturdayOf(day));
  }, [day]); // eslint-disable-line react-hooks/exhaustive-deps

  const setSel = (referee: number | null, date: string | null = day) => {
    const next = new URLSearchParams();
    if (referee) next.set("referee", String(referee));
    if (date) next.set("date", date);
    setParams(next, { replace: true });
  };

  const days = useMemo(
    () => [...new Set((data.data?.venues ?? []).flatMap((v) => v.matches.map((m) => m.date)))].sort(),
    [data.data],
  );
  const referees = (data.data?.referees ?? []).filter(
    (r) => matchesText([r.name, r.location], query) && (!day || r.days.some((d) => d.date === day)),
  );
  const referee = data.data?.referees.find((r) => r.referee_id === selected) ?? null;

  return (
    <div>
      <PageHeader title="Mapa" subtitle="Obiekty z meczami i trasy sędziów: dom → mecze → dom" />
      <ErrorBanner message={data.error} />
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <button className={!day ? "btn-primary" : "btn-secondary"} onClick={() => setSel(selected, null)}>
          Cały okres
        </button>
        {days.map((d) => (
          <button key={d} className={day === d ? "btn-primary" : "btn-secondary"} onClick={() => setSel(selected, d)}>
            {shortDay(d)}
          </button>
        ))}
        <span className="ml-auto flex flex-wrap gap-3 text-xs text-zinc-500">
          <Legend color={FILL.full} label="obsadzony" />
          <Legend color={FILL.partial} label="częściowo" />
          <Legend color={FILL.none} label="brak obsady" />
        </span>
      </div>
      {data.loading && !data.data ? (
        <Loading />
      ) : !data.data ? null : (
        <div className="grid gap-4 lg:grid-cols-[18rem_1fr]">
          <div className="card flex max-h-[70vh] flex-col overflow-hidden">
            <div className="border-b border-zinc-100 p-3">
              <SearchBox value={query} onChange={setQuery} placeholder="Szukaj sędziego" />
            </div>
            <div className="flex-1 overflow-y-auto">
              {referees.length === 0 ? (
                <EmptyState title="Brak przypisań" hint="Trasy pojawią się po zapisaniu obsady." />
              ) : (
                referees.map((r) => (
                  <RefereeItem key={r.referee_id} r={r} day={day} active={r.referee_id === selected} onClick={() => setSel(r.referee_id === selected ? null : r.referee_id)} />
                ))
              )}
            </div>
          </div>
          <MapView data={data.data} referee={referee} day={day} />
        </div>
      )}
    </div>
  );
}

function Legend({ color, label }: { color: string; label: string }) {
  return (
    <span className="flex items-center gap-1.5">
      <span className="size-2.5 rounded-full" style={{ background: color }} />
      {label}
    </span>
  );
}

function RefereeItem({ r, day, active, onClick }: { r: MapReferee; day: string | null; active: boolean; onClick: () => void }) {
  const shown = r.days.filter((d) => !day || d.date === day);
  const km = shown.reduce((s, d) => s + d.km, 0);
  return (
    <button onClick={onClick} className={`block w-full border-b border-zinc-100 px-4 py-2.5 text-left text-sm hover:bg-zinc-50 ${active ? "bg-brand-50" : ""}`}>
      <div className="flex items-center justify-between gap-2">
        <span className="font-medium">{r.name}</span>
        <span className="flex items-center gap-1 text-xs tabular-nums text-zinc-500">
          <Car className="size-3.5" />
          {km.toFixed(0)} km
        </span>
      </div>
      <div className="text-xs text-zinc-500">
        {r.location} · {shown.reduce((s, d) => s + d.stops.length, 0)} mecz.
      </div>
      {active &&
        shown.map((d) => (
          <div key={d.date} className="mt-2 text-xs">
            <div className="flex items-center gap-1.5 font-medium" style={{ color: DAY_COLORS[r.days.indexOf(d) % DAY_COLORS.length] }}>
              <span className="size-2 rounded-full" style={{ background: DAY_COLORS[r.days.indexOf(d) % DAY_COLORS.length] }} />
              {shortDay(d.date)} · {d.km.toFixed(0)} km
            </div>
            <ol className="ml-3.5 mt-0.5 space-y-0.5 text-zinc-600">
              <li className="flex items-center gap-1">
                <Home className="size-3" /> dom
              </li>
              {d.stops.map((s, j) => (
                <li key={s.match_id}>
                  {j + 1}. {s.time} {s.venue} <span className="text-zinc-400">({ROLE_LABELS[s.role]})</span>
                </li>
              ))}
            </ol>
          </div>
        ))}
    </button>
  );
}

function MapView({ data, referee, day }: { data: PeriodMap; referee: MapReferee | null; day: string | null }) {
  const el = useRef<HTMLDivElement>(null);
  const map = useRef<L.Map | null>(null);
  const layer = useRef<L.LayerGroup | null>(null);

  useEffect(() => {
    if (!el.current || map.current) return;
    map.current = L.map(el.current, { zoomControl: true }).setView(WARSAW, 9);
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 18,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    }).addTo(map.current);
    layer.current = L.layerGroup().addTo(map.current);
    return () => {
      map.current?.remove();
      map.current = null;
    };
  }, []);

  useEffect(() => {
    const m = map.current;
    const g = layer.current;
    if (!m || !g) return;
    g.clearLayers();
    let cancelled = false;
    const bounds: LatLng[] = [];

    const routeDays = referee ? referee.days.filter((d) => !day || d.date === day) : [];
    const routeVenues = new Set(routeDays.flatMap((d) => d.stops.map((s) => s.venue_id)));
    for (const v of data.venues) {
      const ms = v.matches.filter((x) => !day || x.date === day);
      if (!ms.length) continue;
      const dim = referee !== null && !routeVenues.has(v.id);
      L.circleMarker(v.point, {
        radius: 6 + Math.min(ms.length, 6),
        color: "#fff",
        weight: 2,
        fillColor: venueFill(v, day),
        fillOpacity: dim ? 0.25 : 0.9,
        opacity: dim ? 0.4 : 1,
      })
        .bindPopup(
          `<div class="text-sm"><div class="font-semibold">${esc(v.name)}</div>` +
            ms
              .map(
                (x) =>
                  `<div class="mt-1"><span class="tabular-nums">${shortDay(x.date)} ${x.time}</span> ${esc(x.home_team)} – ${esc(x.away_team)}` +
                  `<div class="text-xs text-zinc-500">${esc(x.league)} · obsada ${x.filled}/${x.required}</div></div>`,
              )
              .join("") +
            "</div>",
        )
        .addTo(g);
      if (!referee) bounds.push(v.point);
    }

    if (referee && routeDays.length) {
      L.marker(referee.home, { icon: HOME_ICON }).bindTooltip(`Dom: ${esc(referee.name)}`).addTo(g);
      bounds.push(referee.home);
      routeDays.forEach((d) => {
        const color = DAY_COLORS[referee.days.indexOf(d) % DAY_COLORS.length];
        const pts: LatLng[] = [referee.home, ...d.stops.map((s) => s.point), referee.home];
        bounds.push(...pts);
        d.stops.forEach((s, i) =>
          L.marker(s.point, { icon: badge(String(i + 1), color), zIndexOffset: 500 })
            .bindTooltip(`${shortDay(d.date)} ${s.time} · ${esc(s.venue)}<br>${esc(s.label)}`)
            .addTo(g),
        );
        const straight = L.polyline(pts, { color, weight: 3, opacity: 0.5, dashArray: "6 6" }).addTo(g);
        api
          .routeShape(pts)
          .then((r) => {
            if (cancelled || !r.exact) return;
            g.removeLayer(straight);
            L.polyline(r.path, { color, weight: 4, opacity: 0.85 }).addTo(g);
          })
          .catch(() => undefined);
      });
    }
    if (bounds.length) m.fitBounds(L.latLngBounds(bounds), { padding: [30, 30], maxZoom: 13 });
    return () => {
      cancelled = true;
    };
  }, [data, referee, day]);

  return <div ref={el} className="card z-0 h-[70vh] min-h-96 overflow-hidden" />;
}
