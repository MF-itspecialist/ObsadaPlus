import { useState, type FormEvent } from "react";

import type { Match, MatchInput, Venue } from "../types";
import { hhmm } from "../utils/format";
import { ErrorBanner } from "./Feedback";
import { Field } from "./RefereeForm";

interface Props {
  initial?: Match;
  defaultDate: string;
  venues: Venue[];
  onSubmit: (data: MatchInput) => Promise<void>;
  onCancel: () => void;
}

export default function MatchForm({ initial, defaultDate, venues, onSubmit, onCancel }: Props) {
  const [form, setForm] = useState<MatchInput>(
    initial
      ? {
          external_id: initial.external_id,
          date: initial.date,
          start_time: hhmm(initial.start_time),
          estimated_end_time: hhmm(initial.estimated_end_time),
          league: initial.league,
          home_team: initial.home_team,
          away_team: initial.away_team,
          venue_id: initial.venue_id,
          required_referees: initial.required_referees,
          observer_required: initial.observer_required,
          status: initial.status === "CANCELLED" ? "CANCELLED" : null,
        }
      : {
          external_id: null,
          date: defaultDate,
          start_time: "14:00",
          estimated_end_time: "15:45",
          league: "",
          home_team: "",
          away_team: "",
          venue_id: venues[0]?.id ?? 0,
          required_referees: 1,
          observer_required: null,
        },
  );
  const [error, setError] = useState<string | null>(null);
  const set = <K extends keyof MatchInput>(key: K, value: MatchInput[K]) => setForm((f) => ({ ...f, [key]: value }));

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    try {
      await onSubmit(form);
    } catch (err) {
      setError((err as Error).message);
    }
  };

  return (
    <form onSubmit={submit} className="space-y-4">
      <ErrorBanner message={error} />
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        <Field label="Data">
          <input className="input" type="date" required value={form.date} onChange={(e) => set("date", e.target.value)} />
        </Field>
        <Field label="Początek">
          <input className="input" type="time" required value={form.start_time} onChange={(e) => set("start_time", e.target.value)} />
        </Field>
        <Field label="Koniec (szac.)">
          <input className="input" type="time" required value={form.estimated_end_time} onChange={(e) => set("estimated_end_time", e.target.value)} />
        </Field>
        <Field label="Gospodarz">
          <input className="input" required value={form.home_team} onChange={(e) => set("home_team", e.target.value)} />
        </Field>
        <Field label="Gość">
          <input className="input" required value={form.away_team} onChange={(e) => set("away_team", e.target.value)} />
        </Field>
        <Field label="Liga">
          <input className="input" value={form.league} onChange={(e) => set("league", e.target.value)} />
        </Field>
        <Field label="Obiekt">
          <select className="input" value={form.venue_id} onChange={(e) => set("venue_id", Number(e.target.value))}>
            {venues.map((v) => (
              <option key={v.id} value={v.id}>
                {v.name} ({v.city})
              </option>
            ))}
          </select>
        </Field>
        <Field label="Liczba sędziów">
          <select className="input" value={form.required_referees} onChange={(e) => set("required_referees", Number(e.target.value))}>
            <option value={1}>1 (sędzia główny)</option>
            <option value={3}>3 (G + A1 + A2)</option>
            <option value={4}>4 (+ techniczny)</option>
          </select>
        </Field>
        <Field label="ID zewnętrzne">
          <input className="input" value={form.external_id ?? ""} onChange={(e) => set("external_id", e.target.value || null)} />
        </Field>
      </div>
      <label className="flex items-start gap-2 text-sm">
        <input
          type="checkbox"
          className="mt-1"
          checked={!!form.observer_required}
          onChange={(e) => set("observer_required", e.target.checked ? true : initial ? false : null)}
        />
        <span>
          Obserwator na meczu
          <span className="block text-xs text-zinc-500">
            {initial
              ? initial.observer_manual
                ? "Ustawione ręcznie: zmiana lig w Ustawieniach tego meczu nie zmieni."
                : "Ustawione automatycznie wg lig w Ustawieniach. Zmiana tutaj zostanie zapamiętana dla tego meczu."
              : "Bez zaznaczenia: automatycznie, jeśli liga jest na liście w Ustawieniach."}
          </span>
        </span>
      </label>
      {initial && (
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={form.status === "CANCELLED"} onChange={(e) => set("status", e.target.checked ? "CANCELLED" : null)} />
          Mecz odwołany
        </label>
      )}
      <div className="flex justify-end gap-2">
        <button type="button" className="btn-secondary" onClick={onCancel}>
          Anuluj
        </button>
        <button type="submit" className="btn-primary">
          Zapisz
        </button>
      </div>
    </form>
  );
}
