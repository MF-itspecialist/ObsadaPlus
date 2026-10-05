import { useState, type FormEvent } from "react";

import type { Venue, VenueInput } from "../types";
import { ErrorBanner } from "./Feedback";
import { Field } from "./RefereeForm";

interface Props {
  initial?: Venue;
  onSubmit: (data: VenueInput) => Promise<void>;
  onCancel: () => void;
}

export default function VenueForm({ initial, onSubmit, onCancel }: Props) {
  const [form, setForm] = useState<VenueInput>(
    initial
      ? { name: initial.name, city: initial.city, address: initial.address, latitude: initial.latitude, longitude: initial.longitude }
      : { name: "", city: "Warszawa", address: "", latitude: 52.2297, longitude: 21.0122 },
  );
  const [error, setError] = useState<string | null>(null);

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
      <Field label="Nazwa">
        <input className="input" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
      </Field>
      <div className="grid grid-cols-2 gap-3">
        <Field label="Miasto">
          <input className="input" value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })} />
        </Field>
        <Field label="Adres">
          <input className="input" value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} />
        </Field>
        <Field label="Szerokość geogr.">
          <input className="input" type="number" step="0.0001" required value={form.latitude} onChange={(e) => setForm({ ...form, latitude: Number(e.target.value) })} />
        </Field>
        <Field label="Długość geogr.">
          <input className="input" type="number" step="0.0001" required value={form.longitude} onChange={(e) => setForm({ ...form, longitude: Number(e.target.value) })} />
        </Field>
      </div>
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
