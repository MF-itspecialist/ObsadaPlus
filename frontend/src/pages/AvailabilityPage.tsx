import { useEffect, useState } from "react";

import Avatar from "../components/Avatar";
import { ErrorBanner, InfoBanner, Loading, PageHeader } from "../components/Feedback";
import { usePeriod } from "../context/PeriodContext";
import { useAsync } from "../hooks/useAsync";
import { api } from "../services/api";
import type { Availability, Referee } from "../types";
import { dayName, datesBetween, formatDate } from "../utils/dates";
import { hhmm } from "../utils/format";

interface DayForm {
  allDay: boolean;
  unavailable: boolean;
  from: string;
  to: string;
}

type FormState = Record<string, DayForm>; // klucz: `${refereeId}|${date}`

const key = (refereeId: number, date: string) => `${refereeId}|${date}`;
const EMPTY_DAY: DayForm = { allDay: false, unavailable: false, from: "", to: "" };

function toForm(a: Availability | undefined): DayForm {
  if (!a) return EMPTY_DAY;
  if (!a.available) return { ...EMPTY_DAY, unavailable: true };
  if (!a.available_from && !a.available_to) return { ...EMPTY_DAY, allDay: true };
  return { allDay: false, unavailable: false, from: hhmm(a.available_from).replace("—", ""), to: hhmm(a.available_to).replace("—", "") };
}

function toPayload(refereeId: number, date: string, d: DayForm): Availability | null {
  if (d.unavailable) return { referee_id: refereeId, date, available: false, available_from: null, available_to: null };
  if (d.allDay) return { referee_id: refereeId, date, available: true, available_from: null, available_to: null };
  if (d.from || d.to) return { referee_id: refereeId, date, available: true, available_from: d.from || null, available_to: d.to || null };
  return null; // brak zgłoszenia
}

export default function AvailabilityPage() {
  const { period } = usePeriod();
  const days = datesBetween(period.date_from, period.date_to);
  const data = useAsync(
    () => Promise.all([api.referees(), api.availability(period)]),
    [period.date_from],
  );
  const [form, setForm] = useState<FormState>({});
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!data.data) return;
    const [referees, availability] = data.data;
    const next: FormState = {};
    referees.forEach((r) =>
      days.forEach((d) => {
        next[key(r.id, d)] = toForm(availability.find((a) => a.referee_id === r.id && a.date === d));
      }),
    );
    setForm(next);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data.data]);

  const update = (refereeId: number, date: string, patch: Partial<DayForm>) =>
    setForm((f) => ({ ...f, [key(refereeId, date)]: { ...(f[key(refereeId, date)] ?? EMPTY_DAY), ...patch } }));

  const save = async () => {
    if (!data.data) return;
    const items = data.data[0].flatMap((r) =>
      days.map((d) => toPayload(r.id, d, form[key(r.id, d)] ?? EMPTY_DAY)).filter((x): x is Availability => x !== null),
    );
    setSaving(true);
    try {
      await api.saveAvailability(items);
      setInfo(`Zapisano dyspozycyjność (${items.length} wpisów).`);
      data.reload();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const referees: Referee[] = data.data?.[0].filter((r) => r.active) ?? [];

  return (
    <div>
      <PageHeader title="Dyspozycyjność" subtitle="Godziny, w których sędziowie mogą prowadzić mecze">
        <button className="btn-primary" onClick={save} disabled={saving || !data.data}>
          Zapisz zmiany
        </button>
      </PageHeader>
      <ErrorBanner message={error ?? data.error} onClose={() => setError(null)} />
      <InfoBanner message={info} onClose={() => setInfo(null)} />
      <p className="mb-4 text-sm text-zinc-500">
        Puste pola oznaczają brak zgłoszenia — sędzia jest wtedy traktowany jako niedostępny (zmienisz to w Ustawieniach).
      </p>
      <div className="card overflow-hidden"><div className="overflow-x-auto">
        {data.loading && !data.data ? (
          <Loading />
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Sędzia</th>
                {days.map((d) => (
                  <th key={d} className="capitalize">
                    {dayName(d)} <span className="font-normal text-zinc-400">{formatDate(d)}</span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {referees.map((r) => (
                <tr key={r.id}>
                  <td className="whitespace-nowrap">
                    <div className="flex items-center gap-3">
                      <Avatar name={`${r.first_name} ${r.last_name}`} />
                      <div>
                        <div className="font-medium">
                          {r.first_name} {r.last_name}
                        </div>
                        <div className="text-xs text-zinc-500">{r.city}</div>
                      </div>
                    </div>
                  </td>
                  {days.map((d) => {
                    const v = form[key(r.id, d)] ?? EMPTY_DAY;
                    const timesDisabled = v.allDay || v.unavailable;
                    return (
                      <td key={d}>
                        <div className="flex flex-wrap items-center gap-2">
                          <label className="text-xs text-zinc-400">od</label>
                          <input type="time" className="input w-28 py-1.5" disabled={timesDisabled} value={v.from} onChange={(e) => update(r.id, d, { from: e.target.value })} />
                          <label className="text-xs text-zinc-400">do</label>
                          <input type="time" className="input w-28 py-1.5" disabled={timesDisabled} value={v.to} onChange={(e) => update(r.id, d, { to: e.target.value })} />
                        </div>
                        <div className="mt-2 flex gap-2 text-xs">
                          <label className={`flex cursor-pointer items-center gap-1.5 rounded-full px-2.5 py-1 ring-1 ring-inset transition ${v.allDay ? "bg-emerald-50 text-emerald-700 ring-emerald-600/20" : "text-zinc-500 ring-zinc-200 hover:bg-zinc-50"}`}>
                            <input type="checkbox" className="accent-emerald-600" checked={v.allDay} onChange={(e) => update(r.id, d, { allDay: e.target.checked, unavailable: false })} />
                            cały dzień
                          </label>
                          <label className={`flex cursor-pointer items-center gap-1.5 rounded-full px-2.5 py-1 ring-1 ring-inset transition ${v.unavailable ? "bg-red-50 text-red-700 ring-red-600/20" : "text-zinc-500 ring-zinc-200 hover:bg-zinc-50"}`}>
                            <input type="checkbox" className="accent-red-600" checked={v.unavailable} onChange={(e) => update(r.id, d, { unavailable: e.target.checked, allDay: false })} />
                            niedostępny
                          </label>
                        </div>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div></div>
    </div>
  );
}
