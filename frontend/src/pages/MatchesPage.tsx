import { useRef, useState } from "react";

import { ErrorBanner, InfoBanner, Loading, PageHeader } from "../components/Feedback";
import MatchForm from "../components/MatchForm";
import Modal from "../components/Modal";
import StatusBadge from "../components/StatusBadge";
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
      const r = await api.importMatches(file);
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
      <PageHeader title="Mecze">
        <input ref={fileRef} type="file" accept=".json,.csv" className="hidden" onChange={(e) => importFile(e.target.files?.[0])} />
        <button className="btn-secondary" onClick={() => fileRef.current?.click()}>
          Import JSON / CSV
        </button>
        <button className="btn-primary" onClick={() => setEditing("new")} disabled={!venues.data?.length}>
          + Dodaj mecz
        </button>
      </PageHeader>
      <ErrorBanner message={error ?? matches.error} onClose={() => setError(null)} />
      <InfoBanner message={info} onClose={() => setInfo(null)} />
      <div className="card overflow-x-auto">
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
                    <div>{formatDate(m.date)}</div>
                    <div className="text-xs text-slate-500">{dayName(m.date)}</div>
                  </td>
                  <td className="whitespace-nowrap">
                    {hhmm(m.start_time)}–{hhmm(m.estimated_end_time)}
                  </td>
                  <td>{m.league}</td>
                  <td>{m.home_team}</td>
                  <td>{m.away_team}</td>
                  <td>
                    <div>{m.venue.name}</div>
                    <div className="text-xs text-slate-500">{m.venue.city}</div>
                  </td>
                  <td>{m.assignments.map((a) => a.referee_name).join(", ") || <span className="text-slate-400">—</span>}</td>
                  <td>
                    <StatusBadge status={m.status} />
                  </td>
                  <td className="whitespace-nowrap text-right">
                    <button className="btn-link mr-3" onClick={() => setEditing(m)}>
                      Edytuj
                    </button>
                    <button className="btn-link text-red-600" onClick={() => remove(m)}>
                      Usuń
                    </button>
                  </td>
                </tr>
              ))}
              {matches.data?.length === 0 && (
                <tr>
                  <td colSpan={9} className="py-6 text-center text-slate-500">
                    Brak meczów w wybranym weekendzie.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </div>
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
