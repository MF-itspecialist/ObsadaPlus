import { Plus } from "lucide-react";
import { useState } from "react";

import Avatar from "../components/Avatar";
import { ErrorBanner, Loading, PageHeader } from "../components/Feedback";
import { LicenseList } from "../components/Licenses";
import Modal from "../components/Modal";
import RowActions from "../components/RowActions";
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
      <PageHeader title="Sędziowie" subtitle="Dostępność i obciążenie sędziów w wybranych dniach obsadowych (pt–pon)">
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
                <th>Sędzia</th>
                <th>Licencje</th>
                {days.map((d) => (
                  <th key={d} className="text-center capitalize">
                    {dayName(d)}
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
                      <div>
                        <div className="font-medium whitespace-nowrap">
                          {r.first_name} {r.last_name} {!r.active && <Tag>nieaktywny</Tag>}
                        </div>
                        <div className="text-xs text-zinc-500">{r.location_label}</div>
                      </div>
                    </div>
                  </td>
                  <td className="min-w-52 max-w-72">
                    <LicenseList licenses={r.licenses} />
                  </td>
                  {load.map((d) => (
                    <td key={d.date} className="text-center">
                      <div className="text-base font-semibold tabular-nums">{d.matches}</div>
                      <div className="mt-0.5 inline-flex items-center gap-1 text-[11px] whitespace-nowrap text-zinc-500">
                        <span className={`size-1.5 rounded-full ${availabilityDot(d.availability)}`} />
                        {shortAvailability(d.availability)}
                      </div>
                    </td>
                  ))}
                  <td>
                    <LoadBar value={matches_in_period} max={r.max_matches_per_weekend} />
                  </td>
                  <td className="whitespace-nowrap">
                    <RowActions onEdit={() => setEditing(r)} onDelete={() => remove(r)} />
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

function shortAvailability(text: string): string {
  if (text === "dostępny cały dzień") return "cały dzień";
  if (text.startsWith("dostępny ")) return text.replace("dostępny ", "");
  if (text === "brak zgłoszenia") return "brak zgłosz.";
  return text;
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
