import { useState, type FormEvent } from "react";

import type { Venue, VenueInput } from "../types";
import AddressFields from "./AddressFields";
import { ErrorBanner } from "./Feedback";
import { Field } from "./RefereeForm";

interface Props {
  initial?: Venue;
  onSubmit: (data: VenueInput) => Promise<void>;
  onCancel: () => void;
}

export default function VenueForm({ initial, onSubmit, onCancel }: Props) {
  const [form, setForm] = useState<VenueInput>(
    initial ? { name: initial.name, city: initial.city, address: initial.address } : { name: "", city: "Warszawa", address: "" },
  );
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

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
      <Field label="Nazwa obiektu">
        <input className="input" required placeholder="np. Stadion KS Ursus" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
      </Field>
      <div className="grid grid-cols-2 gap-3">
        <AddressFields
          address={form.address}
          city={form.city}
          savedLabel={initial ? [initial.address, initial.city].filter(Boolean).join(", ") : undefined}
          onChange={(address, city) => setForm((f) => ({ ...f, address, city }))}
        />
      </div>
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
