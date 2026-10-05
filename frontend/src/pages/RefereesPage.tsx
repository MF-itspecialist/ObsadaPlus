import { Pencil, Plus, Trash2 } from "lucide-react";
import { useState } from "react";

import Avatar from "../components/Avatar";
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
      <PageHeader title="Sędziowie" subtitle="Dostępność i obciążenie sędziów w wybranym weekendzie">
        <button className="btn-primary" onClick={() => setEditing("new")}>
          <Plus className="size-4" /> Dodaj sędziego
        </button>
      </PageHeader>
      <ErrorBanner message={error ?? overview.error} onClose={() => setError(null)} />
      <div className="card overflow-hidden"><div className="overflow-x-auto">
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
                <th>Mecze weekend</th>
                <th className="text-right">Akcje</th>
              </tr>
            </thead>
            <tbody>
              {overview.data?.map(({ referee: r, days: load, matches_in_period }) => (
                <tr key={r.id} className={r.active ? "" : "text-zinc-400"}>
                  <td>
                    <div className="flex items-center gap-3">
                      <Avatar name={`${r.first_name} ${r.last_name}`} muted={!r.active} />
                      {r.first_name}
                    </div>
                  </td>
                  <td className="font-medium">
                    {r.last_name} {!r.active && <Tag>nieaktywny</Tag>}
                  </td>
                  <td>{r.city}</td>
                  <td className="text-xs">
                    {load.map((d) => (
                      <div key={d.date} className="flex items-center gap-1.5">
                        <span className={`size-1.5 rounded-full ${availabilityDot(d.availability)}`} />
                        <span className="w-8 text-zinc-400 capitalize">{dayName(d.date).slice(0, 3)}</span>
                        <span className="text-zinc-600">{d.availability}</span>
                      </div>
                    ))}
                  </td>
                  {load.map((d) => (
                    <td key={d.date} className="text-center tabular-nums">
                      {d.matches}
                    </td>
                  ))}
                  <td>
                    <LoadBar value={matches_in_period} max={r.max_matches_per_weekend} />
                  </td>
                  <td className="whitespace-nowrap text-right">
                    <button className="icon-btn" onClick={() => setEditing(r)} aria-label="Edytuj" title="Edytuj">
                      <Pencil className="size-4" />
                    </button>
                    <button className="icon-btn hover:bg-red-50 hover:text-red-600" onClick={() => remove(r)} aria-label="Usuń" title="Usuń">
                      <Trash2 className="size-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div></div>
      {editing && (
        <Modal title={editing === "new" ? "Nowy sędzia" : "Edycja sędziego"} onClose={() => setEditing(null)}>
          <RefereeForm initial={editing === "new" ? undefined : editing} onSubmit={save} onCancel={() => setEditing(null)} />
        </Modal>
      )}
    </div>
  );
}

function availabilityDot(text: string): string {
  if (text.startsWith("dostępny cały")) return "bg-emerald-500";
  if (text.startsWith("dostępny")) return "bg-amber-400";
  if (text === "niedostępny") return "bg-red-500";
  return "bg-zinc-300";
}

/** Pasek wykorzystania limitu weekendowego. */
function LoadBar({ value, max }: { value: number; max: number }) {
  const pct = max ? Math.min(100, (value / max) * 100) : 0;
  const color = pct >= 100 ? "bg-red-500" : pct >= 60 ? "bg-amber-400" : "bg-brand-500";
  return (
    <div className="flex min-w-28 items-center gap-2">
      <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-zinc-100">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs tabular-nums text-zinc-600">
        <span className="font-semibold text-zinc-900">{value}</span>/{max}
      </span>
    </div>
  );
}
