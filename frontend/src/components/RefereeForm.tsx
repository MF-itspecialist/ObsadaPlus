import { useState, type FormEvent } from "react";

import type { Referee, RefereeInput } from "../types";
import AddressFields from "./AddressFields";
import { ErrorBanner } from "./Feedback";
import { LicensePicker } from "./Licenses";

const EMPTY: RefereeInput = {
  first_name: "",
  last_name: "",
  city: "Warszawa",
  address: "",
  licenses: [],
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
    const { id: _id, district: _d, location_label: _l, latitude: _lat, longitude: _lng, ...rest } = initial;
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
    <form onSubmit={submit} className="space-y-5">
      <ErrorBanner message={error} />
      <Section title="Dane sędziego">
        <Field label="Imię">
          <input className="input" required value={form.first_name} onChange={(e) => set("first_name", e.target.value)} />
        </Field>
        <Field label="Nazwisko">
          <input className="input" required value={form.last_name} onChange={(e) => set("last_name", e.target.value)} />
        </Field>
      </Section>

      <fieldset>
        <legend className="text-sm font-semibold text-zinc-800">Licencje</legend>
        <p className="mb-2 text-xs text-zinc-500">Kliknij, aby przydzielić lub odebrać licencję. Można wybrać kilka.</p>
        <LicensePicker value={form.licenses} onChange={(licenses) => set("licenses", licenses)} />
      </fieldset>

      <Section title="Miejsce zamieszkania" hint="Na tej podstawie liczymy dojazdy na mecze. Dzielnica uzupełni się sama.">
        <AddressFields
          address={form.address}
          city={form.city}
          savedLabel={initial?.location_label}
          onChange={(address, city) => setForm((f) => ({ ...f, address, city }))}
        />
      </Section>

      <Section title="Ile meczów może sędziować">
        <Field label="Najchętniej w jeden dzień">
          <input className="input" type="number" min={0} value={form.preferred_matches_per_day} onChange={num("preferred_matches_per_day")} />
        </Field>
        <Field label="Maksymalnie w jeden dzień">
          <input className="input" type="number" min={0} value={form.max_matches_per_day} onChange={num("max_matches_per_day")} />
        </Field>
        <Field label="Najchętniej w weekend (pt–pon)">
          <input className="input" type="number" min={0} value={form.preferred_matches_per_weekend} onChange={num("preferred_matches_per_weekend")} />
        </Field>
        <Field label="Maksymalnie w weekend (pt–pon)">
          <input className="input" type="number" min={0} value={form.max_matches_per_weekend} onChange={num("max_matches_per_weekend")} />
        </Field>
      </Section>

      <Field label="Notatki">
        <textarea className="input" rows={2} value={form.notes ?? ""} onChange={(e) => set("notes", e.target.value || null)} />
      </Field>
      <label className="flex items-center gap-2 text-sm">
        <input type="checkbox" checked={form.active} onChange={(e) => set("active", e.target.checked)} />
        Aktywny (bierze udział w obsadzie)
      </label>
      <div className="flex justify-end gap-2">
        <button type="button" className="btn-secondary" onClick={onCancel}>
          Anuluj
        </button>
        <button type="submit" className="btn-primary" disabled={saving}>
          {saving ? "Zapisywanie…" : "Zapisz"}
        </button>
      </div>
    </form>
  );
}

export function Section({ title, hint, children }: { title: string; hint?: string; children: React.ReactNode }) {
  return (
    <fieldset>
      <legend className="text-sm font-semibold text-zinc-800">{title}</legend>
      {hint && <p className="mb-2 text-xs text-zinc-500">{hint}</p>}
      <div className="mt-2 grid grid-cols-2 gap-3">{children}</div>
    </fieldset>
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
