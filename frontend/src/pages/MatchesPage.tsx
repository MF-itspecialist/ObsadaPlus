import { Plus, Upload } from "lucide-react";
import { useRef, useState } from "react";

import Avatar from "../components/Avatar";
import { EmptyState, ErrorBanner, InfoBanner, Loading, PageHeader } from "../components/Feedback";
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

export default function MatchesPage() {
  const { period } = usePeriod();
  const matches = useAsync(() => api.matches(period), [period.date_from]);
  const venues = useAsync(() => api.venues(), []);
  const [editing, setEditing] = useState<Match | "new" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const [includePast, setIncludePast] = useState(false);

  const save = async (data: MatchInput) => {
    if (editing === "new") await api.createMatch(data);
    else if (editing) await api.updateMatch(editing.id, data);
    setEditing(null);
    matches.reload();
  };

  const remove = async (m: Match) => {
    if (!confirm(`Usunąć mecz ${m.home_team} – ${m.away_team}?`)) return;
    try {
      await api.deleteMatch(m.id);
      matches.reload();
    } catch (e) {
      setError((e as Error).message);
    }
  };

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
              {matches.data?.map((m) => (
                <tr key={m.id}>
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
                    <div className="text-xs text-zinc-500">{m.venue.city}</div>
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
                    <RowActions onEdit={() => setEditing(m)} onDelete={() => remove(m)} />
                  </td>
                </tr>
              ))}
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
