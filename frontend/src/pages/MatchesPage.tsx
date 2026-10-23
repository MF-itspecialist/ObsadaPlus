import { Plus, Upload } from "lucide-react";
import { memo, useCallback, useMemo, useRef, useState } from "react";

import Avatar from "../components/Avatar";
import { EmptyState, ErrorBanner, InfoBanner, Loading, PageHeader } from "../components/Feedback";
import { FilterRow, LoadMoreRow, SearchBox, SelectFilter, matchesText, regionOptions, uniqueSorted, useIncremental } from "../components/Filters";
import MatchForm from "../components/MatchForm";
import Modal from "../components/Modal";
import RowActions from "../components/RowActions";
import StatusBadge, { Tag } from "../components/StatusBadge";
import { usePeriod } from "../context/PeriodContext";
import { useAsync } from "../hooks/useAsync";
import { api } from "../services/api";
import type { Match, MatchInput } from "../types";
import { dayName, formatDate } from "../utils/dates";
import { hhmm } from "../utils/format";
import { leagueLevel } from "../utils/leagues";

interface MatchFilter {
  query: string;
  level: string;
  region: string;
  city: string;
}

const EMPTY_FILTER: MatchFilter = { query: "", level: "", region: "", city: "" };

function matchesFilter(m: Match, f: MatchFilter): boolean {
  return (
    (!f.level || leagueLevel(m.league).label === f.level) &&
    (!f.region || m.venue.region === f.region) &&
    (!f.city || m.venue.city === f.city) &&
    matchesText([m.home_team, m.away_team, m.league, m.venue.name, m.venue.city, m.venue.address], f.query)
  );
}

export default function MatchesPage() {
  const { period } = usePeriod();
  const matches = useAsync(() => api.matches(period), [period.date_from]);
  const venues = useAsync(() => api.venues(), []);
  const [editing, setEditing] = useState<Match | "new" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const [includePast, setIncludePast] = useState(false);
  const [filter, setFilter] = useState<MatchFilter>(EMPTY_FILTER);
  const all = useMemo(() => matches.data ?? [], [matches.data]);
  const filtered = useMemo(() => all.filter((m) => matchesFilter(m, filter)), [all, filter]);
  const page = useIncremental(filtered, filtered);
  const levels = useMemo(
    () => [...new Map(all.map((m) => [leagueLevel(m.league).label, leagueLevel(m.league).rank])).entries()].sort((a, b) => a[1] - b[1]).map(([l]) => l),
    [all],
  );
  const regions = useMemo(() => regionOptions(all.map((m) => m.venue.region)), [all]);
  const cities = useMemo(
    () => uniqueSorted(all.filter((m) => !filter.region || m.venue.region === filter.region).map((m) => m.venue.city)),
    [all, filter.region],
  );
  const set = (patch: Partial<MatchFilter>) => setFilter((f) => ({ ...f, ...patch }));

  const save = async (data: MatchInput) => {
    if (editing === "new") await api.createMatch(data);
    else if (editing) await api.updateMatch(editing.id, data);
    setEditing(null);
    matches.reload();
  };

  const { reload } = matches;
  const remove = useCallback(
    async (m: Match) => {
      if (!confirm(`Usunąć mecz ${m.home_team} – ${m.away_team}?`)) return;
      try {
        await api.deleteMatch(m.id);
        reload();
      } catch (e) {
        setError((e as Error).message);
      }
    },
    [reload],
  );

  const importFile = async (file: File | undefined) => {
    if (!file) return;
    try {
      const r = await api.importMatches(file, includePast);
      setInfo(`Import: dodano ${r.created}, zaktualizowano ${r.updated}.${r.errors.length ? ` Błędy: ${r.errors.join("; ")}` : ""}`);
      matches.reload();
      venues.reload();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  return (
    <div>
      <PageHeader title="Mecze" subtitle="Terminarz wybranego weekendu, dodawanie i import meczów">
        <input ref={fileRef} type="file" accept=".json,.csv" className="hidden" onChange={(e) => importFile(e.target.files?.[0])} />
        <label className="flex items-center gap-2 text-sm text-zinc-600" title="Dotyczy eksportu z Łączy Nas Piłka — np. terminarz sezonu 2025/26 jako dane robocze">
          <input type="checkbox" checked={includePast} onChange={(e) => setIncludePast(e.target.checked)} />
          także rozegrane mecze
        </label>
        <button className="btn-secondary" onClick={() => fileRef.current?.click()}>
          <Upload className="size-4" /> Import JSON / CSV
        </button>
        <button className="btn-primary" onClick={() => setEditing("new")} disabled={!venues.data?.length}>
          <Plus className="size-4" /> Dodaj mecz
        </button>
      </PageHeader>
      <ErrorBanner message={error ?? matches.error} onClose={() => setError(null)} />
      <InfoBanner message={info} onClose={() => setInfo(null)} />
      <FilterRow active={Object.values(filter).some(Boolean)} onClear={() => setFilter(EMPTY_FILTER)} shown={filtered.length} total={all.length} noun="meczów">
        <SearchBox value={filter.query} onChange={(query) => set({ query })} placeholder="Szukaj: drużyna, liga, obiekt, adres" />
        <SelectFilter label="Klasa rozgrywkowa" all="Wszystkie klasy" options={levels} value={filter.level} onChange={(level) => set({ level })} />
        <SelectFilter label="Podokręg" all="Wszystkie podokręgi" options={regions} value={filter.region} onChange={(region) => set({ region, city: "" })} />
        <SelectFilter label="Miejscowość boiska" all="Wszystkie miejscowości" options={cities} value={filter.city} onChange={(city) => set({ city })} />
      </FilterRow>
      <div className="card overflow-hidden"><div className="overflow-x-auto">
        {matches.loading && !matches.data ? (
          <Loading />
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Data</th>
                <th>Godzina</th>
                <th>Liga</th>
                <th>Gospodarz</th>
                <th>Gość</th>
                <th>Miejsce</th>
                <th>Sędzia</th>
                <th>Status</th>
                <th className="text-right">Akcje</th>
              </tr>
            </thead>
            <tbody>
              {page.shown.map((m) => (
                <MatchRow key={m.id} match={m} onEdit={setEditing} onDelete={remove} />
              ))}
              {page.hasMore && <LoadMoreRow colSpan={9} rest={page.rest} onMore={page.more} />}
              {all.length > 0 && filtered.length === 0 && (
                <tr>
                  <td colSpan={9} className="py-10 text-center text-sm text-zinc-500">
                    Żaden mecz nie pasuje do filtra.
                  </td>
                </tr>
              )}
              {matches.data?.length === 0 && (
                <tr>
                  <td colSpan={9}>
                    <EmptyState title="Brak meczów w wybranym weekendzie" hint="Dodaj mecz ręcznie albo zaimportuj plik JSON / CSV." />
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </div></div>
      {editing && venues.data && (
        <Modal title={editing === "new" ? "Nowy mecz" : "Edycja meczu"} onClose={() => setEditing(null)} wide>
          <MatchForm
            initial={editing === "new" ? undefined : editing}
            defaultDate={period.date_from}
            venues={venues.data}
            onSubmit={save}
            onCancel={() => setEditing(null)}
          />
        </Modal>
      )}
    </div>
  );
}

const MatchRow = memo(function MatchRow({ match: m, onEdit, onDelete }: {
  match: Match;
  onEdit: (m: Match) => void;
  onDelete: (m: Match) => void;
}) {
  return (
    <tr>
      <td className="whitespace-nowrap">
        <div className="font-medium tabular-nums">{formatDate(m.date)}</div>
        <div className="text-xs text-zinc-500 capitalize">{dayName(m.date)}</div>
      </td>
      <td className="whitespace-nowrap tabular-nums">
        <span className="font-medium">{hhmm(m.start_time)}</span>
        <span className="text-zinc-400">–{hhmm(m.estimated_end_time)}</span>
      </td>
      <td>{m.league && <Tag tone="brand">{m.league}</Tag>}</td>
      <td className="font-medium">{m.home_team}</td>
      <td className="font-medium">{m.away_team}</td>
      <td>
        <div>{m.venue.name}</div>
        <div className="text-xs text-zinc-500">
          {[m.venue.address, [m.venue.postal_code, m.venue.city].filter(Boolean).join(" ")].filter(Boolean).join(", ")}
        </div>
      </td>
      <td>
        {m.assignments.length ? (
          <div className="space-y-1">
            {m.assignments.map((a) => (
              <div key={a.id} className="flex items-center gap-2 whitespace-nowrap">
                <Avatar name={a.referee_name} size="sm" />
                {a.referee_name}
              </div>
            ))}
          </div>
        ) : (
          <span className="text-zinc-400">—</span>
        )}
      </td>
      <td>
        <StatusBadge status={m.status} />
      </td>
      <td className="whitespace-nowrap">
        <RowActions onEdit={() => onEdit(m)} onDelete={() => onDelete(m)} />
      </td>
    </tr>
  );
});
