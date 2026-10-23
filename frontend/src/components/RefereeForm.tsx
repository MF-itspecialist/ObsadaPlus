import { X } from "lucide-react";
import { useState, type FormEvent } from "react";

import { useAsync } from "../hooks/useAsync";
import { api } from "../services/api";
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
  preferred_leagues: [],
  avoided_clubs: [],
  conflict_clubs: [],
  own_region_only: false,
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

      <PreferencesSection form={form} set={set} />

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

// --- Preferencje i ograniczenia ------------------------------------------------------

function PreferencesSection({
  form,
  set,
}: {
  form: RefereeInput;
  set: <K extends keyof RefereeInput>(key: K, value: RefereeInput[K]) => void;
}) {
  const levels = useAsync(() => api.leagueLevels(), []);
  const clubs = useAsync(() => api.clubs(), []);
  const toggle = (level: string) =>
    set("preferred_leagues", form.preferred_leagues.includes(level) ? form.preferred_leagues.filter((l) => l !== level) : [...form.preferred_leagues, level]);

  return (
    <fieldset className="space-y-4">
      <legend className="text-sm font-semibold text-zinc-800">Preferencje i ograniczenia</legend>
      <div>
        <span className="label">Preferowane ligi</span>
        <p className="mb-2 text-xs text-zinc-500">Inne ligi dostanie tylko, gdy nie ma lepszego kandydata. Nic nie zaznaczone = bez preferencji.</p>
        <div className="flex flex-wrap gap-1.5">
          {(levels.data ?? []).map((level) => {
            const on = form.preferred_leagues.includes(level);
            return (
              <button
                key={level}
                type="button"
                onClick={() => toggle(level)}
                className={`rounded-full px-2.5 py-1 text-xs ring-1 ring-inset transition ${
                  on ? "bg-brand-50 font-medium text-brand-700 ring-brand-600/30" : "text-zinc-600 ring-zinc-200 hover:bg-zinc-50"
                }`}
              >
                {level}
              </button>
            );
          })}
        </div>
      </div>
      <datalist id="obsada-clubs">
        {(clubs.data ?? []).map((c) => (
          <option key={c} value={c} />
        ))}
      </datalist>
      <ClubList
        label="Konflikt interesów — nigdy nie sędziuje meczów tych klubów"
        hint="Klub, w którym gra, trenuje albo działa sędzia lub jego rodzina. Obejmuje też rezerwy (II, III)."
        value={form.conflict_clubs}
        onChange={(v) => set("conflict_clubs", v)}
        tone="red"
      />
      <ClubList
        label="Woli unikać klubów"
        hint="Mecze tych klubów dostanie tylko wtedy, gdy nikt inny nie może."
        value={form.avoided_clubs}
        onChange={(v) => set("avoided_clubs", v)}
        tone="amber"
      />
      <label className="flex items-center gap-2 text-sm">
        <input type="checkbox" checked={form.own_region_only} onChange={(e) => set("own_region_only", e.target.checked)} />
        Sędziuje tylko w swoim podokręgu
      </label>
    </fieldset>
  );
}

function ClubList({
  label,
  hint,
  value,
  onChange,
  tone,
}: {
  label: string;
  hint: string;
  value: string[];
  onChange: (v: string[]) => void;
  tone: "red" | "amber";
}) {
  const [draft, setDraft] = useState("");
  const add = () => {
    const name = draft.trim();
    if (name && !value.includes(name)) onChange([...value, name]);
    setDraft("");
  };
  const chip = tone === "red" ? "bg-red-50 text-red-700 ring-red-600/20" : "bg-amber-50 text-amber-800 ring-amber-600/20";
  return (
    <div>
      <span className="label">{label}</span>
      <p className="mb-2 text-xs text-zinc-500">{hint}</p>
      {value.length > 0 && (
        <div className="mb-2 flex flex-wrap gap-1.5">
          {value.map((c) => (
            <span key={c} className={`inline-flex items-center gap-1 rounded-full py-1 pr-1.5 pl-2.5 text-xs ring-1 ring-inset ${chip}`}>
              {c}
              <button type="button" className="rounded-full p-0.5 hover:bg-white/60" onClick={() => onChange(value.filter((x) => x !== c))} aria-label={`Usuń ${c}`}>
                <X className="size-3" />
              </button>
            </span>
          ))}
        </div>
      )}
      <div className="flex gap-2">
        <input
          className="input"
          list="obsada-clubs"
          placeholder="Nazwa klubu, np. Agape Białołęka"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              add();
            }
          }}
        />
        <button type="button" className="btn-secondary" onClick={add} disabled={!draft.trim()}>
          Dodaj
        </button>
      </div>
    </div>
  );
}
