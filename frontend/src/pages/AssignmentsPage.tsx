import { ChevronDown, Eye, Hand, RefreshCw, Sparkles, Trash2, TriangleAlert, UserPlus, X } from "lucide-react";
import { useState } from "react";

import CandidatePicker from "../components/CandidatePicker";
import Avatar from "../components/Avatar";
import Explanation from "../components/Explanation";
import { EmptyState, ErrorBanner, InfoBanner, Loading, PageHeader } from "../components/Feedback";
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
import { dayName, formatDate } from "../utils/dates";
import { groupBy, hhmm } from "../utils/format";

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
        <PreviewView preview={preview} />
      ) : board.loading && !board.data ? (
        <Loading />
      ) : (
        <BoardView
          items={board.data ?? []}
          onPick={setPicker}
          onRemove={removeAssignment}
        />
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

type PreviewEntry = { kind: "assigned"; match: MatchInfo; item: ProposedAssignment } | { kind: "unassigned"; match: MatchInfo; item: UnassignedSlot };

function PreviewView({ preview }: { preview: GenerationPreview }) {
  const entries: PreviewEntry[] = [
    ...preview.assignments.map((item) => ({ kind: "assigned" as const, match: item.match, item })),
    ...preview.unassigned.map((item) => ({ kind: "unassigned" as const, match: item.match, item })),
  ].sort((a, b) => (a.match.date + a.match.start_time).localeCompare(b.match.date + b.match.start_time));

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
      {groupBy(entries, (e) => e.match.date).map(([date, dayEntries]) => (
        <DaySection key={date} date={date} count={dayEntries.length}>
          {dayEntries.map((e) =>
            e.kind === "assigned" ? (
              <MatchCard key={`${e.match.match_id}-${e.item.role}`} match={e.match} state={e.item.conflict ? "conflict" : "ok"}>
                <RefereeLine
                  role={e.item.role}
                  name={e.item.referee_name}
                  distance={e.item.distance_km}
                  travel={e.item.travel_minutes}
                  scoreValue={e.item.score}
                  manual={e.item.manually_modified}
                  conflict={e.item.conflict}
                  explanation={<Explanation data={e.item.explanation} total={e.item.score} />}
                />
              </MatchCard>
            ) : (
              <MatchCard key={`${e.match.match_id}-${e.item.role}`} match={e.match} state="empty">
                <UnassignedReasons slot={e.item} />
              </MatchCard>
            ),
          )}
        </DaySection>
      ))}
    </div>
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

function BoardView({
  items,
  onPick,
  onRemove,
}: {
  items: BoardItem[];
  onPick: (p: PickerState) => void;
  onRemove: (a: Assignment) => void;
}) {
  if (items.length === 0)
    return (
      <div className="card">
        <EmptyState title="Brak meczów w wybranym weekendzie" hint="Dodaj mecze w zakładce Mecze albo wybierz inny weekend." />
      </div>
    );
  return (
    <div>
      {groupBy(items, (m) => m.date).map(([date, matches]) => (
        <DaySection key={date} date={date} count={matches.length}>
          {matches.map((m) => {
            const info: MatchInfo = {
              match_id: m.match_id,
              date: m.date,
              start_time: hhmm(m.start_time),
              end_time: hhmm(m.estimated_end_time),
              league: m.league,
              home_team: m.home_team,
              away_team: m.away_team,
              venue_name: m.venue_name,
            };
            const title = `${hhmm(m.start_time)} ${m.home_team} – ${m.away_team}`;
            const hasConflict = m.assignments.some((a) => a.conflict);
            const state = hasConflict ? "conflict" : m.status === "ASSIGNED" ? "ok" : m.status === "CANCELLED" ? "cancelled" : "empty";
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
                      distance={a.distance_km}
                      travel={a.travel_minutes}
                      scoreValue={a.score}
                      manual={a.manually_modified}
                      conflict={a.conflict}
                      explanation={<Explanation data={a.explanation} total={a.score} />}
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
          })}
        </DaySection>
      ))}
    </div>
  );
}

// --- Wspólne elementy ---------------------------------------------------------------

function DaySection({ date, count, children }: { date: string; count: number; children: React.ReactNode }) {
  return (
    <section className="mb-8">
      <div className="sticky top-[61px] z-10 -mx-1 mb-3 flex items-center gap-3 bg-zinc-50/90 px-1 py-2 backdrop-blur">
        <h2 className="text-sm font-semibold tracking-wide text-zinc-900 uppercase">{dayName(date)}</h2>
        <span className="text-sm text-zinc-500 tabular-nums">{formatDate(date)}</span>
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
  distance: number | null;
  travel: number | null;
  scoreValue: number | null;
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
        <MetricChips distance={props.distance} travel={props.travel} scoreValue={props.scoreValue} />
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
