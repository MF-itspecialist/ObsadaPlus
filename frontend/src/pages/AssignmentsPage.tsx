import { useState } from "react";

import CandidatePicker from "../components/CandidatePicker";
import Explanation from "../components/Explanation";
import { ErrorBanner, InfoBanner, Loading, PageHeader } from "../components/Feedback";
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
import { groupBy, hhmm, km, minutes, score } from "../utils/format";

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
      <PageHeader title="Obsada">
        {preview ? (
          <>
            <button className="btn-secondary" onClick={() => setPreview(null)} disabled={busy}>
              Odrzuć propozycję
            </button>
            <button className="btn-primary" onClick={confirmPreview} disabled={busy}>
              ZATWIERDŹ OBSADĘ
            </button>
          </>
        ) : (
          <>
            <button className="btn-secondary" onClick={() => generate("FULL")} disabled={busy}>
              Generuj całość od nowa
            </button>
            <button className="btn-primary" onClick={() => generate("KEEP_MANUAL")} disabled={busy}>
              {busy ? "Generowanie…" : "GENERUJ OBSADĘ"}
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
  const rows: [string, string | number][] = [
    ["Liczba meczów", stats.matches_total],
    ["Obsadzone", stats.matches_assigned],
    ["Nieobsadzone", stats.matches_unassigned],
    ["Aktywni sędziowie", stats.active_referees],
    ["Średnio meczów / sędziego", stats.avg_matches_per_referee.toFixed(2)],
    ["Średnia odległość", `${stats.avg_distance_km.toFixed(1)} km`],
    ["Łącznie kilometrów", `${stats.total_distance_km.toFixed(1)} km`],
    ["Konflikty", stats.conflicts],
  ];
  return (
    <div className="card mb-4 grid grid-cols-2 gap-px overflow-hidden bg-slate-200 sm:grid-cols-4">
      {rows.map(([label, value]) => (
        <div key={label} className="bg-white px-4 py-3">
          <div className="text-xs uppercase tracking-wide text-slate-500">{label}</div>
          <div className="text-xl font-semibold tabular-nums">{value}</div>
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
      <div className="mb-4 rounded-md border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-800">
        To jest <strong>podgląd</strong> — obsada nie została jeszcze zapisana.{" "}
        {preview.params.mode === "FULL" ? "Tryb: generowanie całości od nowa." : "Ręczne przypisania zostały zachowane."}
      </div>
      <StatsPanel stats={preview.stats} />
      {groupBy(entries, (e) => e.match.date).map(([date, dayEntries]) => (
        <DaySection key={date} date={date}>
          {dayEntries.map((e) =>
            e.kind === "assigned" ? (
              <MatchCard key={`${e.match.match_id}-${e.item.role}`} match={e.match}>
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
              <MatchCard key={`${e.match.match_id}-${e.item.role}`} match={e.match} unassigned>
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
  return (
    <div className="text-sm">
      <div className="font-semibold text-red-600">BRAK OBSADY ({ROLE_LABELS[slot.role]})</div>
      <div className="mt-1 text-slate-600">Najczęstsze powody:</div>
      <ul className="ml-4 list-disc text-slate-700">
        {slot.reasons.map((r) => (
          <li key={r.code}>
            {r.label} <span className="text-slate-400">({r.count} sędz.)</span>
          </li>
        ))}
        {slot.reasons.length === 0 && <li>brak aktywnych sędziów</li>}
      </ul>
      {slot.rejected_examples.length > 0 && (
        <details className="mt-1 text-xs text-slate-500">
          <summary className="cursor-pointer">Szczegóły odrzuceń</summary>
          <ul className="mt-1 space-y-0.5">
            {slot.rejected_examples.map((x) => (
              <li key={x.referee}>
                <strong>{x.referee}</strong>: {x.reason}
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
  if (items.length === 0) return <p className="py-10 text-center text-sm text-slate-500">Brak meczów w wybranym weekendzie.</p>;
  return (
    <div>
      {groupBy(items, (m) => m.date).map(([date, matches]) => (
        <DaySection key={date} date={date}>
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
            return (
              <MatchCard key={m.match_id} match={info} unassigned={m.status === "UNASSIGNED"} status={<StatusBadge status={m.status} />}>
                {m.required_roles.map((role) => {
                  const a = m.assignments.find((x) => x.role === role);
                  if (!a) {
                    return (
                      <div key={role} className="flex flex-wrap items-center justify-between gap-2 text-sm">
                        <span className="font-semibold text-red-600">BRAK OBSADY ({ROLE_LABELS[role]})</span>
                        <button className="btn-secondary" onClick={() => onPick({ matchId: m.match_id, role, title: `Przypisz: ${title}` })}>
                          Przypisz ręcznie / pokaż powody
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
                          <button className="btn-link text-red-600" onClick={() => onRemove(a)}>
                            Usuń obsadę
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

function DaySection({ date, children }: { date: string; children: React.ReactNode }) {
  return (
    <section className="mb-6">
      <h2 className="mb-2 text-sm font-bold uppercase tracking-wider text-emerald-800">
        {dayName(date)} · {formatDate(date)}
      </h2>
      <div className="space-y-3">{children}</div>
    </section>
  );
}

function MatchCard({
  match,
  unassigned,
  status,
  children,
}: {
  match: MatchInfo;
  unassigned?: boolean;
  status?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className={`card flex flex-col gap-3 p-4 sm:flex-row ${unassigned ? "border-red-200" : ""}`}>
      <div className="sm:w-64 sm:shrink-0">
        <div className="text-2xl font-semibold tabular-nums">{match.start_time}</div>
        <div className="font-medium">
          {match.home_team}
          <span className="text-slate-400"> vs </span>
          {match.away_team}
        </div>
        <div className="text-sm text-slate-500">{match.venue_name}</div>
        <div className="mt-1 flex items-center gap-2">
          {match.league && <Tag>{match.league}</Tag>}
          {status}
        </div>
      </div>
      <div className="flex-1 space-y-3">{children}</div>
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
      <div className="flex flex-wrap items-baseline gap-x-6 gap-y-1 text-sm">
        <div>
          <div className="text-xs uppercase text-slate-500">{ROLE_LABELS[props.role]}</div>
          <div className="text-base font-semibold">
            {props.name} {props.manual && <Tag tone="amber">ręcznie</Tag>}
          </div>
        </div>
        <Metric label="Odległość" value={km(props.distance)} />
        <Metric label="Transport" value={minutes(props.travel)} />
        <Metric label="SCORE" value={score(props.scoreValue)} />
        <div className="ml-auto flex gap-3">
          <button className="btn-link" onClick={() => setOpen(!open)}>
            {open ? "Ukryj" : "Dlaczego?"}
          </button>
          {props.actions}
        </div>
      </div>
      {props.conflict && <div className="mt-1 text-sm font-medium text-red-600">⚠ Konflikt: {props.conflict}</div>}
      {open && <div className="mt-2 rounded-md bg-slate-50 p-3">{props.explanation}</div>}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-xs uppercase text-slate-500">{label}</div>
      <div className="tabular-nums">{value}</div>
    </div>
  );
}
