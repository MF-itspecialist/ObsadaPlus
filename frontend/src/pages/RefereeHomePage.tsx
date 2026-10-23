import { CalendarCheck, ExternalLink, MapPin, Users } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { ErrorBanner, InfoBanner, Loading } from "../components/Feedback";
import { AccountBox } from "../components/Layout";
import { Tag } from "../components/StatusBadge";
import { useAsync } from "../hooks/useAsync";
import { api } from "../services/api";
import type { Availability, MyMatch, OwnAvailabilitySave } from "../types";
import { addDays, datesBetween, dayName, formatDate, fromIso, shortDay, upcomingSaturday } from "../utils/dates";
import { hhmm } from "../utils/format";

const WEEKENDS = 6;

/** Panel sędziego: opublikowane mecze i zgłaszanie dyspozycyjności na najbliższe weekendy. */
export default function RefereeHomePage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-6 md:py-10">
      <div className="card mb-6 overflow-hidden">
        <div className="flex items-center gap-3 px-5 pt-5 pb-4">
          <div className="flex size-9 items-center justify-center rounded-xl bg-gradient-to-br from-brand-500 to-violet-500 text-lg font-bold text-white shadow-md shadow-brand-500/30">
            +
          </div>
          <div className="leading-tight">
            <div className="text-[15px] font-semibold tracking-tight">Panel sędziego</div>
            <div className="text-xs text-zinc-500">Obsada+ · Twoje mecze i dyspozycyjność</div>
          </div>
        </div>
        <AccountBox />
      </div>
      <MyMatches />
      <MyAvailability />
    </div>
  );
}

// --- Mecze ---------------------------------------------------------------------------

function MyMatches() {
  const matches = useAsync(() => api.myMatches(), []);
  return (
    <section className="mb-10">
      <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold tracking-wide text-zinc-900 uppercase">
        <Users className="size-4 text-brand-600" /> Moje mecze
      </h2>
      <ErrorBanner message={matches.error} />
      {matches.loading && !matches.data ? (
        <Loading />
      ) : !matches.data?.length ? (
        <div className="card px-5 py-6 text-sm text-zinc-500">
          Nie masz meczów w opublikowanej obsadzie. Mecze pojawią się tutaj, gdy obsadzający opublikuje obsadę.
        </div>
      ) : (
        <div className="space-y-3">
          {matches.data.map((m) => (
            <MatchItem key={m.match_id} m={m} />
          ))}
        </div>
      )}
    </section>
  );
}

function MatchItem({ m }: { m: MyMatch }) {
  const mapUrl = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent([m.venue_name, m.venue_address].filter(Boolean).join(", "))}`;
  return (
    <div className={`card flex gap-4 p-4 ${m.cancelled ? "opacity-60" : ""}`}>
      <div className="w-16 shrink-0 text-center">
        <div className="text-xs font-medium whitespace-nowrap text-zinc-500">{shortDay(m.date)}</div>
        <div className="text-xl font-semibold tracking-tight tabular-nums">{m.start_time}</div>
      </div>
      <div className="min-w-0 flex-1 space-y-1.5">
        <div className="font-semibold leading-snug">
          {m.home_team} <span className="font-normal text-zinc-400">–</span> {m.away_team}
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          <Tag tone="brand">{m.role_label}</Tag>
          {m.league && <Tag>{m.league}</Tag>}
          {m.cancelled && <Tag tone="red">mecz odwołany</Tag>}
        </div>
        <a className="flex items-start gap-1.5 text-sm text-zinc-600 hover:text-brand-700" href={mapUrl} target="_blank" rel="noreferrer">
          <MapPin className="mt-0.5 size-3.5 shrink-0" />
          <span>
            {m.venue_name}
            {m.venue_address && <span className="text-zinc-400"> · {m.venue_address}</span>}
            {m.distance_km != null && <span className="text-zinc-400"> · ok. {Math.round(m.distance_km)} km</span>}
            <ExternalLink className="ml-1 inline size-3" />
          </span>
        </a>
        {m.crew.length > 0 && (
          <div className="text-sm text-zinc-500">
            {m.crew.map((c) => (
              <span key={c.role} className="mr-3 inline-block">
                {c.role_label}: <span className="text-zinc-700">{c.referee_name ?? "jeszcze nieobsadzone"}</span>
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// --- Dyspozycyjność --------------------------------------------------------------------

type Mode = "none" | "all" | "hours" | "off";

interface DayState {
  mode: Mode;
  from: string;
  to: string;
}

const NONE: DayState = { mode: "none", from: "", to: "" };

function toState(a: Availability | undefined): DayState {
  if (!a) return NONE;
  if (!a.available) return { ...NONE, mode: "off" };
  if (!a.available_from && !a.available_to) return { ...NONE, mode: "all" };
  return { mode: "hours", from: hhmm(a.available_from).replace("—", ""), to: hhmm(a.available_to).replace("—", "") };
}

const same = (a: DayState, b: DayState) => a.mode === b.mode && (a.mode !== "hours" || (a.from === b.from && a.to === b.to));

const MODES: { mode: Mode; label: string; tone: string }[] = [
  { mode: "all", label: "Cały dzień", tone: "bg-emerald-600 text-white" },
  { mode: "hours", label: "Godziny", tone: "bg-brand-600 text-white" },
  { mode: "off", label: "Nie mogę", tone: "bg-red-600 text-white" },
];

function MyAvailability() {
  const today = useAsync(() => api.serverToday(), []);
  // Dni obsadowe piątek–poniedziałek kolejnych weekendów, od najbliższego.
  const weekends = useMemo(() => {
    if (!today.data) return [];
    const first = upcomingSaturday(fromIso(today.data.today));
    return Array.from({ length: WEEKENDS }, (_, i) => {
      const sat = addDays(first, 7 * i);
      return datesBetween(addDays(sat, -1), addDays(sat, 2));
    });
  }, [today.data]);
  const period = weekends.length ? { date_from: weekends[0][0], date_to: weekends[weekends.length - 1][3] } : null;
  const saved = useAsync(() => (period ? api.myAvailability(period) : Promise.resolve([])), [period?.date_from]);

  const [form, setForm] = useState<Record<string, DayState>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  const initial = useMemo(() => {
    const out: Record<string, DayState> = {};
    weekends.flat().forEach((d) => (out[d] = toState(saved.data?.find((a) => a.date === d))));
    return out;
  }, [weekends, saved.data]);
  useEffect(() => setForm(initial), [initial]);

  const byAdmin = useMemo(() => new Set((saved.data ?? []).filter((a) => !a.declared_by_referee).map((a) => a.date)), [saved.data]);
  const changed = Object.keys(form).filter((d) => initial[d] && !same(form[d], initial[d]));
  const locked = (d: string) => !today.data || d <= today.data.today;

  const save = async () => {
    const data: OwnAvailabilitySave = { items: [], cleared: [] };
    for (const d of changed) {
      const s = form[d];
      if (s.mode === "none") data.cleared.push(d);
      else if (s.mode === "off") data.items.push({ date: d, available: false, available_from: null, available_to: null });
      else if (s.mode === "all") data.items.push({ date: d, available: true, available_from: null, available_to: null });
      else {
        if (!s.from || !s.to) return setError(`${dayName(d)} ${formatDate(d)}: podaj godziny „od” i „do”.`);
        data.items.push({ date: d, available: true, available_from: s.from, available_to: s.to });
      }
    }
    setBusy(true);
    setError(null);
    try {
      await api.saveMyAvailability(data);
      setInfo(`Zapisano zmiany (${changed.length} ${changed.length === 1 ? "dzień" : "dni"}).`);
      saved.reload();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const set = (d: string, patch: Partial<DayState>) => setForm((f) => ({ ...f, [d]: { ...f[d], ...patch } }));

  return (
    <section className="pb-24">
      <h2 className="mb-1 flex items-center gap-2 text-sm font-semibold tracking-wide text-zinc-900 uppercase">
        <CalendarCheck className="size-4 text-brand-600" /> Moja dyspozycyjność
      </h2>
      <p className="mb-4 text-sm text-zinc-500">
        Zaznacz, kiedy możesz sędziować. Bez zgłoszenia nie dostaniesz meczu w danym dniu. Dzisiejszego dnia ani dni minionych nie można już zmienić.
      </p>
      <ErrorBanner message={error ?? today.error ?? saved.error} onClose={() => setError(null)} />
      <InfoBanner message={info} onClose={() => setInfo(null)} />
      {!today.data || (saved.loading && !saved.data) ? (
        <Loading />
      ) : (
        <div className="space-y-5">
          {weekends.map((days) => (
            <div key={days[0]} className="card divide-y divide-zinc-100 overflow-hidden">
              <div className="bg-zinc-50 px-4 py-2 text-xs font-semibold text-zinc-500">
                Weekend {formatDate(days[1]).slice(0, 5)}–{formatDate(days[2]).slice(0, 5)}
              </div>
              {days.map((d) => (
                <DayRow key={d} date={d} state={form[d] ?? NONE} locked={locked(d)} byAdmin={byAdmin.has(d)} onChange={(p) => set(d, p)} />
              ))}
            </div>
          ))}
        </div>
      )}
      {changed.length > 0 && (
        <div className="fixed inset-x-0 bottom-0 z-20 border-t border-zinc-200 bg-white/95 px-4 py-3 backdrop-blur">
          <div className="mx-auto flex max-w-3xl items-center gap-3">
            <span className="flex-1 text-sm text-zinc-600">
              Niezapisane zmiany: {changed.length} {changed.length === 1 ? "dzień" : "dni"}
            </span>
            <button className="btn-secondary" onClick={() => setForm(initial)} disabled={busy}>
              Cofnij
            </button>
            <button className="btn-primary" onClick={save} disabled={busy}>
              {busy ? "Zapisywanie…" : "Zapisz"}
            </button>
          </div>
        </div>
      )}
    </section>
  );
}

function DayRow({
  date,
  state,
  locked,
  byAdmin,
  onChange,
}: {
  date: string;
  state: DayState;
  locked: boolean;
  byAdmin: boolean;
  onChange: (patch: Partial<DayState>) => void;
}) {
  return (
    <div className={`flex flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3 ${locked ? "bg-zinc-50/60" : ""}`}>
      <div className="w-32 shrink-0">
        <div className="text-sm font-medium capitalize">{dayName(date)}</div>
        <div className="text-xs text-zinc-500">
          {formatDate(date)}
          {locked && " · zamknięte"}
          {!locked && byAdmin && state.mode !== "none" && " · wpisał obsadzający"}
        </div>
      </div>
      <div className="flex flex-wrap gap-1.5" role="radiogroup" aria-label={`Dyspozycyjność ${formatDate(date)}`}>
        {MODES.map(({ mode, label, tone }) => {
          const active = state.mode === mode;
          return (
            <button
              key={mode}
              type="button"
              role="radio"
              aria-checked={active}
              disabled={locked}
              onClick={() => onChange({ mode: active ? "none" : mode })}
              className={`rounded-full px-3 py-1.5 text-xs font-medium ring-1 ring-inset transition disabled:cursor-not-allowed ${
                active ? `${tone} ring-transparent` : "text-zinc-600 ring-zinc-200 hover:bg-zinc-50"
              } ${locked && !active ? "opacity-50" : ""}`}
            >
              {label}
            </button>
          );
        })}
      </div>
      {state.mode === "hours" && (
        <div className="flex items-center gap-1.5">
          <input type="time" aria-label="od" className="input w-[6.5rem] px-2 py-1.5" disabled={locked} value={state.from} onChange={(e) => onChange({ from: e.target.value })} />
          <span className="text-zinc-400">–</span>
          <input type="time" aria-label="do" className="input w-[6.5rem] px-2 py-1.5" disabled={locked} value={state.to} onChange={(e) => onChange({ to: e.target.value })} />
        </div>
      )}
      {state.mode === "none" && !locked && <span className="text-xs text-zinc-400">nie zgłoszono</span>}
    </div>
  );
}
