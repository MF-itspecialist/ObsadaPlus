import { useState } from "react";

import { ErrorBanner, Loading, PageHeader } from "../components/Feedback";
import Modal from "../components/Modal";
import RefereeForm from "../components/RefereeForm";
import { Tag } from "../components/StatusBadge";
import { usePeriod } from "../context/PeriodContext";
import { useAsync } from "../hooks/useAsync";
import { api } from "../services/api";
import type { Referee, RefereeInput } from "../types";
import { dayName } from "../utils/dates";

export default function RefereesPage() {
  const { period } = usePeriod();
  const overview = useAsync(() => api.refereesOverview(period), [period.date_from]);
  const [editing, setEditing] = useState<Referee | "new" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const days = overview.data?.[0]?.days.map((d) => d.date) ?? [period.date_from, period.date_to];

  const save = async (data: RefereeInput) => {
    if (editing === "new") await api.createReferee(data);
    else if (editing) await api.updateReferee(editing.id, data);
    setEditing(null);
    overview.reload();
  };

  const remove = async (r: Referee) => {
    if (!confirm(`Usunąć sędziego ${r.first_name} ${r.last_name}? Usunięte zostaną też jego przypisania.`)) return;
    try {
      await api.deleteReferee(r.id);
      overview.reload();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  return (
    <div>
      <PageHeader title="Sędziowie">
        <button className="btn-primary" onClick={() => setEditing("new")}>
          + Dodaj sędziego
        </button>
      </PageHeader>
      <ErrorBanner message={error ?? overview.error} onClose={() => setError(null)} />
      <div className="card overflow-x-auto">
        {overview.loading && !overview.data ? (
          <Loading />
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Imię</th>
                <th>Nazwisko</th>
                <th>Miasto</th>
                <th>Dostępność</th>
                {days.map((d) => (
                  <th key={d} className="text-center">
                    Mecze {dayName(d)}
                  </th>
                ))}
                <th className="text-center">Mecze weekend</th>
                <th className="text-right">Akcje</th>
              </tr>
            </thead>
            <tbody>
              {overview.data?.map(({ referee: r, days: load, matches_in_period }) => (
                <tr key={r.id} className={r.active ? "" : "text-slate-400"}>
                  <td>{r.first_name}</td>
                  <td className="font-medium">
                    {r.last_name} {!r.active && <Tag>nieaktywny</Tag>}
                  </td>
                  <td>{r.city}</td>
                  <td className="text-xs">
                    {load.map((d) => (
                      <div key={d.date}>
                        <span className="text-slate-500">{dayName(d.date).slice(0, 3)}:</span> {d.availability}
                      </div>
                    ))}
                  </td>
                  {load.map((d) => (
                    <td key={d.date} className="text-center tabular-nums">
                      {d.matches}
                    </td>
                  ))}
                  <td className="text-center font-semibold tabular-nums">
                    {matches_in_period}
                    <span className="font-normal text-slate-400"> / {r.max_matches_per_weekend}</span>
                  </td>
                  <td className="whitespace-nowrap text-right">
                    <button className="btn-link mr-3" onClick={() => setEditing(r)}>
                      Edytuj
                    </button>
                    <button className="btn-link text-red-600" onClick={() => remove(r)}>
                      Usuń
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      {editing && (
        <Modal title={editing === "new" ? "Nowy sędzia" : "Edycja sędziego"} onClose={() => setEditing(null)}>
          <RefereeForm initial={editing === "new" ? undefined : editing} onSubmit={save} onCancel={() => setEditing(null)} />
        </Modal>
      )}
    </div>
  );
}
