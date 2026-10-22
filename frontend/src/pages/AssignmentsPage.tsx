import { ChevronDown, Eye, Hand, RefreshCw, Search, Sparkles, Trash2, TriangleAlert, UserPlus, X } from "lucide-react";
import { useMemo, useState } from "react";

import CandidatePicker from "../components/CandidatePicker";
import Avatar from "../components/Avatar";
import Explanation from "../components/Explanation";
import { EmptyState, ErrorBanner, InfoBanner, Loading, PageHeader } from "../components/Feedback";
import { LicenseList } from "../components/Licenses";
import { MetricChips } from "../components/Metrics";
import StatusBadge, { Tag } from "../components/StatusBadge";
import { usePeriod } from "../context/PeriodContext";
import { useAsync } from "../hooks/useAsync";
import { api } from "../services/api";
import {
  ROLE_LABELS,
  type Assignment,
  type BoardItem,
  type GenerationMode,
  type GenerationPreview,
  type GenerationStats,
  type MatchInfo,
  type ProposedAssignment,
  type RefereeRole,
  type UnassignedSlot,
} from "../types";
import { dayName, formatDate, shortDay } from "../utils/dates";
import { groupBy, hhmm } from "../utils/format";
import { leagueLevel, normalize } from "../utils/leagues";

interface PickerState {
  matchId: number;
  role: RefereeRole;
  title: string;
  currentRefereeId?: number;
}

export default function AssignmentsPage() {
  const { period } = usePeriod();
  const board = useAsync(() => api.board(period), [period.date_from]);
  const [preview, setPreview] = useState<GenerationPreview | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [picker, setPicker] = useState<PickerState | null>(null);
  const [filter, setFilter] = useState<Filter>(EMPTY_FILTER);

  const generate = async (mode: GenerationMode) => {
    if (mode === "FULL" && !confirm("Wygenerować całą obsadę od nowa? Ręczne zmiany zostaną nadpisane po zatwierdzeniu.")) return;
    setBusy(true);
    setError(null);
    try {
      setPreview(await api.generate(period, mode));
      setInfo(null);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const confirmPreview = async () => {
    if (!preview) return;
    setBusy(true);
    try {
      const r = await api.confirm(preview.run_id);
      setInfo(`Obsada zapisana: ${r.saved_assignments} przypisań z generatora, ${r.kept_manual} ręcznych zachowanych.`);
      setPreview(null);
      board.reload();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const removeAssignment = async (a: Assignment) => {
    if (!confirm(`Usunąć obsadę: ${a.referee_name}?`)) return;
    try {
      await api.deleteAssignment(a.id);
      board.reload();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  return (
    <div>
      <PageHeader title="Obsada" subtitle={preview ? "Podgląd propozycji generatora — sprawdź i zatwierdź" : "Aktualna obsada weekendu, ręczne zmiany i generowanie"}>
        {preview ? (
          <>
            <button className="btn-secondary" onClick={() => setPreview(null)} disabled={busy}>
              <X className="size-4" /> Odrzuć propozycję
            </button>
            <button className="btn-primary" onClick={confirmPreview} disabled={busy}>
              ZATWIERDŹ OBSADĘ
            </button>
          </>
        ) : (
          <>
            <button className="btn-secondary" onClick={() => generate("FULL")} disabled={busy}>
              <RefreshCw className="size-4" /> Generuj całość od nowa
            </button>
            <button className="btn-primary" onClick={() => generate("KEEP_MANUAL")} disabled={busy}>
              <Sparkles className="size-4" /> {busy ? "Generowanie…" : "GENERUJ OBSADĘ"}
            </button>
          </>
        )}
      </PageHeader>
      <ErrorBanner message={error ?? board.error} onClose={() => setError(null)} />
      <InfoBanner message={info} onClose={() => setInfo(null)} />

      {preview ? (
        <PreviewView preview={preview} filter={filter} onFilter={setFilter} />
      ) : board.loading && !board.data ? (
        <Loading />
      ) : (
        <BoardView items={board.data ?? []} filter={filter} onFilter={setFilter} onPick={setPicker} onRemove={removeAssignment} />
      )}

      {picker && (
        <CandidatePicker
          {...picker}
          onClose={() => setPicker(null)}
          onAssigned={(warning) => {
            setPicker(null);
            setInfo(warning ? `Przypisano ręcznie. ${warning}` : "Przypisano ręcznie.");
            board.reload();
          }}
        />
      )}
    </div>
  );
}

// --- Filtr i układ listy: najpierw nieobsadzone, potem poziomy rozgrywkowe ----------------

interface Filter {
  query: string;
  level: string;
  day: string;
}

const EMPTY_FILTER: Filter = { query: "", level: "", day: "" };

interface Row {
  key: number;
  match: MatchInfo;
  unassigned: boolean;
  search: string; // znormalizowany tekst: drużyny, obiekt, liga, sędziowie
}

interface Section<T extends Row> {
  key: string;
  title: string;
  hint?: string;
  urgent?: boolean;
  rows: T[];
}

const byKickoff = (a: Row, b: Row) => (a.match.date + a.match.start_time).localeCompare(b.match.date + b.match.start_time);

function applyFilter<T extends Row>(rows: T[], f: Filter): T[] {
  const words = normalize(f.query).split(/\s+/).filter(Boolean);
  return rows.filter(
    (r) =>
      words.every((w) => r.search.includes(w)) &&
      (!f.level || leagueLevel(r.match.league).label === f.level) &&
      (!f.day || r.match.date === f.day),
  );
}

function arrange<T extends Row>(rows: T[]): Section<T>[] {
  const open = rows.filter((r) => r.unassigned).sort(byKickoff);
  const done = rows.filter((r) => !r.unassigned);
  const levels = groupBy(done, (r) => leagueLevel(r.match.league).label).sort(
    ([, a], [, b]) => leagueLevel(a[0].match.league).rank - leagueLevel(b[0].match.league).rank,
  );
  return [
    ...(open.length ? [{ key: "open", title: "Do obsadzenia", hint: "mecze z brakującym sędzią", urgent: true, rows: open }] : []),
    ...levels.map(([label, list]) => ({ key: label, title: label, rows: list.sort(byKickoff) })),
  ];
}

function searchText(...parts: (string | null | undefined)[]): string {
  return normalize(parts.filter(Boolean).join(" "));
}

function FilterBar({ rows, filter, onChange, shown }: { rows: Row[]; filter: Filter; onChange: (f: Filter) => void; shown: number }) {
  const levels = useMemo(
    () =>
      [...new Map(rows.map((r) => [leagueLevel(r.match.league).label, leagueLevel(r.match.league).rank])).entries()].sort((a, b) => a[1] - b[1]),
    [rows],
  );
  const days = useMemo(() => [...new Set(rows.map((r) => r.match.date))].sort(), [rows]);
  const active = filter.query || filter.level || filter.day;
  return (
    <div className="mb-6 flex flex-wrap items-center gap-3">
      <div className="relative w-full max-w-md">
        <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-zinc-400" />
        <input
          className="input pr-9 pl-9"
          type="search"
          placeholder="Szukaj: drużyna, obiekt, liga lub sędzia"
          value={filter.query}
          onChange={(e) => onChange({ ...filter, query: e.target.value })}
          aria-label="Szukaj meczu"
        />
      </div>
      <select className="input w-auto" value={filter.level} onChange={(e) => onChange({ ...filter, level: e.target.value })} aria-label="Poziom rozgrywek">
        <option value="">Wszystkie poziomy</option>
        {levels.map(([label]) => (
          <option key={label} value={label}>
            {label}
          </option>
        ))}
      </select>
      <select className="input w-auto" value={filter.day} onChange={(e) => onChange({ ...filter, day: e.target.value })} aria-label="Dzień">
        <option value="">Wszystkie dni</option>
        {days.map((d) => (
          <option key={d} value={d}>
            {dayName(d)} {formatDate(d)}
          </option>
        ))}
      </select>
      {active && (
        <button className="btn-link" onClick={() => onChange(EMPTY_FILTER)}>
          <X className="size-3.5" /> Wyczyść filtr
        </button>
      )}
      <span className="text-sm text-zinc-500">{active ? `${shown} z ${rows.length} meczów` : `${rows.length} meczów`}</span>
    </div>
  );
}

function SectionList<T extends Row>({ rows, render }: { rows: T[]; render: (row: T) => React.ReactNode }) {
  const sections = arrange(rows);
  if (sections.length === 0)
    return (
      <div className="card">
        <EmptyState title="Żaden mecz nie pasuje do filtra" hint="Zmień wyszukiwanie albo wyczyść filtr." />
      </div>
    );
  return (
    <>
      {sections.map((sec) => (
        <GroupSection key={sec.key} title={sec.title} hint={sec.hint} urgent={sec.urgent} count={sec.rows.length}>
          {sec.rows.map(render)}
        </GroupSection>
      ))}
    </>
  );
}

// --- Podgląd propozycji generatora ------------------------------------------------

function StatsPanel({ stats }: { stats: GenerationStats }) {
  const rows: [string, string | number, string?][] = [
    ["Liczba meczów", stats.matches_total],
    ["Obsadzone", stats.matches_assigned, "text-emerald-600"],
    ["Nieobsadzone", stats.matches_unassigned, stats.matches_unassigned ? "text-red-600" : undefined],
    ["Aktywni sędziowie", stats.active_referees],
    ["Średnio meczów / sędziego", stats.avg_matches_per_referee.toFixed(2)],
    ["Średnia odległość", `${stats.avg_distance_km.toFixed(1)} km`],
    ["Łącznie kilometrów", `${stats.total_distance_km.toFixed(1)} km`],
    ["Konflikty", stats.conflicts, stats.conflicts ? "text-red-600" : undefined],
  ];
  return (
    <div className="card mb-6 grid grid-cols-2 overflow-hidden sm:grid-cols-4">
      {rows.map(([label, value, tone], i) => (
        <div key={label} className={`px-5 py-4 ${i % 4 !== 0 ? "sm:border-l" : ""} ${i >= 4 ? "border-t" : ""} border-zinc-100`}>
          <div className="text-xs font-medium text-zinc-500">{label}</div>
          <div className={`mt-1 text-2xl font-semibold tracking-tight tabular-nums ${tone ?? ""}`}>{value}</div>
        </div>
      ))}
    </div>
  );
}

const ROLE_ORDER = Object.keys(ROLE_LABELS) as RefereeRole[];

interface PreviewRow extends Row {
  assigned: ProposedAssignment[];
  open: UnassignedSlot[];
}

function previewRows(preview: GenerationPreview): PreviewRow[] {
  const rows = new Map<number, PreviewRow>();
  const rowFor = (match: MatchInfo) => {
    let row = rows.get(match.match_id);
    if (!row) {
      row = { key: match.match_id, match, unassigned: false, search: "", assigned: [], open: [] };
      rows.set(match.match_id, row);
    }
    return row;
  };
  preview.assignments.forEach((a) => rowFor(a.match).assigned.push(a));
  preview.unassigned.forEach((u) => rowFor(u.match).open.push(u));
  return [...rows.values()].map((r) => ({
    ...r,
    unassigned: r.open.length > 0,
    search: searchText(r.match.home_team, r.match.away_team, r.match.venue_name, r.match.league, ...r.assigned.map((a) => a.referee_name)),
  }));
}

function PreviewView({ preview, filter, onFilter }: { preview: GenerationPreview; filter: Filter; onFilter: (f: Filter) => void }) {
  const rows = useMemo(() => previewRows(preview), [preview]);
  const visible = applyFilter(rows, filter);
  const byRole = (a: { role: RefereeRole }, b: { role: RefereeRole }) => ROLE_ORDER.indexOf(a.role) - ROLE_ORDER.indexOf(b.role);

  return (
    <div>
      <div className="mb-5 flex items-start gap-3 rounded-xl bg-amber-50 px-4 py-3 text-sm text-amber-900 ring-1 ring-amber-600/15">
        <Eye className="mt-0.5 size-4 shrink-0 text-amber-500" />
        <span>
          To jest <strong>podgląd</strong> — obsada nie została jeszcze zapisana.{" "}
          {preview.params.mode === "FULL" ? "Tryb: generowanie całości od nowa." : "Ręczne przypisania zostały zachowane."}
        </span>
      </div>
      <StatsPanel stats={preview.stats} />
      <FilterBar rows={rows} filter={filter} onChange={onFilter} shown={visible.length} />
      <SectionList
        rows={visible}
        render={(r) => {
          const lines = [
            ...r.assigned.map((a) => ({ role: a.role, node: <PreviewLine key={a.role} a={a} /> })),
            ...r.open.map((u) => ({ role: u.role, node: <UnassignedReasons key={u.role} slot={u} /> })),
          ].sort(byRole);
          const state = r.unassigned ? "empty" : r.assigned.some((a) => a.conflict) ? "conflict" : "ok";
          return (
            <MatchCard key={r.key} match={r.match} state={state}>
              {lines.map((l) => l.node)}
            </MatchCard>
          );
        }}
      />
    </div>
  );
}

function PreviewLine({ a }: { a: ProposedAssignment }) {
  return (
    <RefereeLine
      role={a.role}
      name={a.referee_name}
      licenses={a.referee_licenses}
      location={a.referee_location}
      distance={a.distance_km}
      travel={a.travel_minutes}
      manual={a.manually_modified}
      conflict={a.conflict}
      explanation={<Explanation data={a.explanation} />}
    />
  );
}

function UnassignedReasons({ slot }: { slot: UnassignedSlot }) {
  const max = Math.max(1, ...slot.reasons.map((r) => r.count));
  return (
    <div className="text-sm">
      <div className="flex items-center gap-2 font-semibold text-red-600">
        <TriangleAlert className="size-4" /> BRAK OBSADY · {ROLE_LABELS[slot.role]}
      </div>
      <div className="mt-3 mb-1.5 text-xs font-medium text-zinc-500">Najczęstsze powody</div>
      <div className="space-y-1.5">
        {slot.reasons.map((r) => (
          <div key={r.code} className="flex items-center gap-3">
            <div className="h-1.5 w-24 shrink-0 overflow-hidden rounded-full bg-red-100">
              <div className="h-full rounded-full bg-red-400" style={{ width: `${(r.count / max) * 100}%` }} />
            </div>
            <span className="text-zinc-700">{r.label}</span>
            <span className="text-xs text-zinc-400">{r.count} sędz.</span>
          </div>
        ))}
        {slot.reasons.length === 0 && <div className="text-zinc-700">brak aktywnych sędziów</div>}
      </div>
      {slot.rejected_examples.length > 0 && (
        <details className="group mt-3 text-xs text-zinc-500">
          <summary className="inline-flex cursor-pointer list-none items-center gap-1 font-medium text-brand-600">
            <ChevronDown className="size-3.5 transition group-open:rotate-180" /> Szczegóły odrzuceń
          </summary>
          <ul className="mt-2 space-y-1">
            {slot.rejected_examples.map((x) => (
              <li key={x.referee}>
                <strong className="text-zinc-700">{x.referee}</strong>: {x.reason}
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}

// --- Zapisana obsada ----------------------------------------------------------------

interface BoardRow extends Row {
  item: BoardItem;
}

function boardRows(items: BoardItem[]): BoardRow[] {
  return items.map((m) => ({
    key: m.match_id,
    item: m,
    match: {
      match_id: m.match_id,
      date: m.date,
      start_time: hhmm(m.start_time),
      end_time: hhmm(m.estimated_end_time),
      league: m.league,
      home_team: m.home_team,
      away_team: m.away_team,
      venue_name: m.venue_name,
    },
    unassigned: m.status !== "CANCELLED" && m.required_roles.some((role) => !m.assignments.some((a) => a.role === role)),
    search: searchText(m.home_team, m.away_team, m.venue_name, m.league, ...m.assignments.map((a) => a.referee_name)),
  }));
}

function BoardView({
  items,
  filter,
  onFilter,
  onPick,
  onRemove,
}: {
  items: BoardItem[];
  filter: Filter;
  onFilter: (f: Filter) => void;
  onPick: (p: PickerState) => void;
  onRemove: (a: Assignment) => void;
}) {
  const rows = useMemo(() => boardRows(items), [items]);
  const visible = applyFilter(rows, filter);
  if (items.length === 0)
    return (
      <div className="card">
        <EmptyState title="Brak meczów w wybranym weekendzie" hint="Dodaj mecze w zakładce Mecze albo wybierz inny weekend." />
      </div>
    );
  return (
    <div>
      <FilterBar rows={rows} filter={filter} onChange={onFilter} shown={visible.length} />
      <SectionList
        rows={visible}
        render={({ item: m, match: info, unassigned }) => {
          const title = `${hhmm(m.start_time)} ${m.home_team} – ${m.away_team}`;
          const hasConflict = m.assignments.some((a) => a.conflict);
          const state = m.status === "CANCELLED" ? "cancelled" : unassigned ? "empty" : hasConflict ? "conflict" : "ok";
          return (
            <MatchCard key={m.match_id} match={info} state={state} status={<StatusBadge status={m.status} />}>
              {m.required_roles.map((role) => {
                const a = m.assignments.find((x) => x.role === role);
                if (!a) {
                  return (
                    <div key={role} className="flex flex-wrap items-center justify-between gap-3">
                      <div className="flex items-center gap-3">
                        <span className="flex size-9 items-center justify-center rounded-full border-2 border-dashed border-red-200 text-red-400">
                          <UserPlus className="size-4" />
                        </span>
                        <div>
                          <div className="text-xs text-zinc-500">{ROLE_LABELS[role]}</div>
                          <div className="text-sm font-semibold text-red-600">Brak obsady</div>
                        </div>
                      </div>
                      <button className="btn-secondary" onClick={() => onPick({ matchId: m.match_id, role, title: `Przypisz: ${title}` })}>
                        <UserPlus className="size-4" /> Przypisz / pokaż powody
                      </button>
                    </div>
                  );
                }
                return (
                  <RefereeLine
                    key={role}
                    role={role}
                    name={a.referee_name}
                    licenses={a.referee_licenses}
                    location={a.referee_location}
                    distance={a.distance_km}
                    travel={a.travel_minutes}
                    manual={a.manually_modified}
                    conflict={a.conflict}
                    explanation={<Explanation data={a.explanation} />}
                    actions={
                      <>
                        <button
                          className="btn-link"
                          onClick={() => onPick({ matchId: m.match_id, role, title: `Zmień sędziego: ${title}`, currentRefereeId: a.referee_id })}
                        >
                          Zmień sędziego
                        </button>
                        <button className="icon-btn hover:bg-red-50 hover:text-red-600" onClick={() => onRemove(a)} aria-label="Usuń obsadę" title="Usuń obsadę">
                          <Trash2 className="size-4" />
                        </button>
                      </>
                    }
                  />
                );
              })}
            </MatchCard>
          );
        }}
      />
    </div>
  );
}

// --- Wspólne elementy ---------------------------------------------------------------

function GroupSection({
  title,
  hint,
  urgent,
  count,
  children,
}: {
  title: string;
  hint?: string;
  urgent?: boolean;
  count: number;
  children: React.ReactNode;
}) {
  return (
    <section className="mb-8">
      <div className="sticky top-[61px] z-10 -mx-1 mb-3 flex items-center gap-3 bg-zinc-50/90 px-1 py-2 backdrop-blur">
        {urgent && <TriangleAlert className="size-4 text-red-500" />}
        <h2 className={`text-sm font-semibold tracking-wide uppercase ${urgent ? "text-red-600" : "text-zinc-900"}`}>{title}</h2>
        {hint && <span className="text-sm text-zinc-500">{hint}</span>}
        <span className="h-px flex-1 bg-zinc-200" />
        <span className="text-xs text-zinc-500">{count} mecz.</span>
      </div>
      <div className="space-y-3">{children}</div>
    </section>
  );
}

const STATE_ACCENT = {
  ok: "bg-emerald-500",
  empty: "bg-red-500",
  conflict: "bg-amber-500",
  cancelled: "bg-zinc-300",
};

function MatchCard({
  match,
  state,
  status,
  children,
}: {
  match: MatchInfo;
  state: keyof typeof STATE_ACCENT;
  status?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="card relative flex flex-col overflow-hidden transition hover:shadow-lift md:flex-row">
      <span className={`absolute inset-y-0 left-0 w-1 ${STATE_ACCENT[state]}`} />
      <div className="flex gap-4 border-zinc-100 p-5 pl-6 md:w-80 md:shrink-0 md:border-r">
        <div className="text-center">
          <div className="text-xs font-medium whitespace-nowrap text-zinc-500">{shortDay(match.date)}</div>
          <div className="text-xl font-semibold tracking-tight tabular-nums">{match.start_time}</div>
          <div className="text-xs text-zinc-400 tabular-nums">{match.end_time}</div>
        </div>
        <div className="min-w-0">
          <div className="leading-snug font-semibold">
            {match.home_team}
            <span className="font-normal text-zinc-400"> vs </span>
            {match.away_team}
          </div>
          <div className="mt-0.5 truncate text-sm text-zinc-500">{match.venue_name}</div>
          <div className="mt-2 flex flex-wrap items-center gap-1.5">
            {match.league && <Tag tone="brand">{match.league}</Tag>}
            {status}
          </div>
        </div>
      </div>
      <div className="flex-1 space-y-4 p-5">{children}</div>
    </div>
  );
}

function RefereeLine(props: {
  role: RefereeRole;
  name: string;
  licenses: string[];
  location: string;
  distance: number | null;
  travel: number | null;
  manual: boolean;
  conflict: string | null;
  explanation: React.ReactNode;
  actions?: React.ReactNode;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div>
      <div className="flex flex-wrap items-center gap-x-6 gap-y-3">
        <div className="flex min-w-48 items-center gap-3">
          <Avatar name={props.name} />
          <div>
            <div className="text-xs text-zinc-500">{ROLE_LABELS[props.role]}</div>
            <div className="flex items-center gap-2 font-semibold">
              {props.name}
              {props.manual && (
                <Tag tone="amber">
                  <Hand className="mr-0.5 size-3" /> ręcznie
                </Tag>
              )}
            </div>
          </div>
        </div>
        <div className="max-w-xs">
          <div className="text-xs text-zinc-500">Licencje</div>
          <LicenseList licenses={props.licenses} />
        </div>
        <div>
          <div className="text-xs text-zinc-500">Mieszka</div>
          <div className="text-zinc-700">{props.location || "—"}</div>
        </div>
        <MetricChips distance={props.distance} travel={props.travel} />
        <div className="ml-auto flex items-center gap-1">
          <button className="btn-link" onClick={() => setOpen(!open)}>
            Dlaczego? <ChevronDown className={`size-3.5 transition ${open ? "rotate-180" : ""}`} />
          </button>
          {props.actions}
        </div>
      </div>
      {props.conflict && (
        <div className="mt-3 flex items-start gap-2 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-900 ring-1 ring-amber-600/15">
          <TriangleAlert className="mt-0.5 size-4 shrink-0 text-amber-500" /> Konflikt: {props.conflict}
        </div>
      )}
      {open && <div className="animate-fade-in mt-3 rounded-xl bg-zinc-50 p-4 ring-1 ring-zinc-950/5">{props.explanation}</div>}
    </div>
  );
}
