import { useState, type FormEvent } from "react";

import type { Referee, RefereeInput } from "../types";
import { ErrorBanner } from "./Feedback";

const EMPTY: RefereeInput = {
  first_name: "",
  last_name: "",
  city: "Warszawa",
  address: "",
  latitude: 52.2297,
  longitude: 21.0122,
  active: true,
  preferred_matches_per_day: 2,
  max_matches_per_day: 3,
  preferred_matches_per_weekend: 4,
  max_matches_per_weekend: 5,
  notes: null,
};

interface Props {
  initial?: Referee;
  onSubmit: (data: RefereeInput) => Promise<void>;
  onCancel: () => void;
}

export default function RefereeForm({ initial, onSubmit, onCancel }: Props) {
  const [form, setForm] = useState<RefereeInput>(() => {
    if (!initial) return EMPTY;
    const { id: _id, ...rest } = initial;
    return rest;
  });
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const set = <K extends keyof RefereeInput>(key: K, value: RefereeInput[K]) => setForm((f) => ({ ...f, [key]: value }));
  const num = (key: keyof RefereeInput) => (e: React.ChangeEvent<HTMLInputElement>) => set(key, Number(e.target.value) as never);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await onSubmit(form);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={submit} className="space-y-4">
      <ErrorBanner message={error} />
      <div className="grid grid-cols-2 gap-3">
        <Field label="Imię">
          <input className="input" required value={form.first_name} onChange={(e) => set("first_name", e.target.value)} />
        </Field>
        <Field label="Nazwisko">
          <input className="input" required value={form.last_name} onChange={(e) => set("last_name", e.target.value)} />
        </Field>
        <Field label="Miasto">
          <input className="input" value={form.city} onChange={(e) => set("city", e.target.value)} />
        </Field>
        <Field label="Adres">
          <input className="input" value={form.address} onChange={(e) => set("address", e.target.value)} />
        </Field>
        <Field label="Szerokość geogr.">
          <input className="input" type="number" step="0.0001" required value={form.latitude} onChange={num("latitude")} />
        </Field>
        <Field label="Długość geogr.">
          <input className="input" type="number" step="0.0001" required value={form.longitude} onChange={num("longitude")} />
        </Field>
        <Field label="Preferowane mecze / dzień">
          <input className="input" type="number" min={0} value={form.preferred_matches_per_day} onChange={num("preferred_matches_per_day")} />
        </Field>
        <Field label="Maks. mecze / dzień">
          <input className="input" type="number" min={0} value={form.max_matches_per_day} onChange={num("max_matches_per_day")} />
        </Field>
        <Field label="Preferowane mecze / weekend (pt–pon)">
          <input className="input" type="number" min={0} value={form.preferred_matches_per_weekend} onChange={num("preferred_matches_per_weekend")} />
        </Field>
        <Field label="Maks. mecze / weekend (pt–pon)">
          <input className="input" type="number" min={0} value={form.max_matches_per_weekend} onChange={num("max_matches_per_weekend")} />
        </Field>
      </div>
      <Field label="Notatki">
        <textarea className="input" rows={2} value={form.notes ?? ""} onChange={(e) => set("notes", e.target.value || null)} />
      </Field>
      <label className="flex items-center gap-2 text-sm">
        <input type="checkbox" checked={form.active} onChange={(e) => set("active", e.target.checked)} />
        Aktywny
      </label>
      <div className="flex justify-end gap-2">
        <button type="button" className="btn-secondary" onClick={onCancel}>
          Anuluj
        </button>
        <button type="submit" className="btn-primary" disabled={saving}>
          Zapisz
        </button>
      </div>
    </form>
  );
}

export function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="label">{label}</span>
      {children}
    </label>
  );
}
