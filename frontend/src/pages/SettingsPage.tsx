import { useEffect, useState } from "react";

import { ErrorBanner, InfoBanner, Loading, PageHeader } from "../components/Feedback";
import { Field } from "../components/RefereeForm";
import { useAsync } from "../hooks/useAsync";
import { api } from "../services/api";
import type { SystemSettings } from "../types";

type NumericKey = {
  [K in keyof SystemSettings]: SystemSettings[K] extends number ? K : never;
}[keyof SystemSettings];

const SECTIONS: { title: string; fields: { key: NumericKey; label: string; step?: number }[] }[] = [
  {
    title: "Logistyka",
    fields: [
      { key: "transport_safety_buffer_minutes", label: "Bufor bezpieczeństwa transportu (min)" },
      { key: "routing_avg_speed_kmh", label: "Średnia prędkość przejazdu (km/h)" },
      { key: "routing_road_factor", label: "Współczynnik krętości dróg", step: 0.05 },
      { key: "default_match_duration_minutes", label: "Domyślny czas meczu przy imporcie (min)" },
    ],
  },
  {
    title: "Wagi scoringu",
    fields: [
      { key: "distance_weight", label: "DISTANCE_WEIGHT (pkt / km)", step: 0.1 },
      { key: "travel_time_weight", label: "TRAVEL_TIME_WEIGHT (pkt / min)", step: 0.1 },
      { key: "daily_match_weight", label: "DAILY_MATCH_WEIGHT" },
      { key: "weekend_match_weight", label: "WEEKEND_MATCH_WEIGHT" },
      { key: "workload_balance_weight", label: "WORKLOAD_BALANCE_WEIGHT" },
      { key: "within_preferred_factor", label: "Mnożnik kary w granicach preferencji", step: 0.05 },
      { key: "over_preferred_factor", label: "Mnożnik kary powyżej preferencji", step: 0.1 },
    ],
  },
];

export default function SettingsPage() {
  const loaded = useAsync(() => api.settings(), []);
  const [form, setForm] = useState<SystemSettings | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  useEffect(() => {
    if (loaded.data) setForm(loaded.data);
  }, [loaded.data]);

  if (!form) return <Loading />;

  const setNum = (k: NumericKey, v: string) => setForm({ ...form, [k]: Number(v) });
  const setBracket = (i: number, j: 0 | 1, v: string) => {
    const brackets = form.distance_brackets.map((b) => [...b] as [number, number]);
    brackets[i][j] = Number(v);
    setForm({ ...form, distance_brackets: brackets });
  };

  const save = async () => {
    try {
      setForm(await api.saveSettings(form));
      setInfo("Ustawienia zapisane. Będą użyte przy kolejnym generowaniu obsady.");
    } catch (e) {
      setError((e as Error).message);
    }
  };

  return (
    <div className="max-w-5xl">
      <PageHeader title="Ustawienia" subtitle="Parametry logistyki i wagi algorytmu obsady">
        <button className="btn-primary" onClick={save}>
          Zapisz
        </button>
      </PageHeader>
      <ErrorBanner message={error ?? loaded.error} onClose={() => setError(null)} />
      <InfoBanner message={info} onClose={() => setInfo(null)} />
      <div className="grid gap-4 md:grid-cols-2">
        {SECTIONS.map((section) => (
          <div key={section.title} className="card space-y-4 p-6">
            <h2 className="font-semibold tracking-tight">{section.title}</h2>
            {section.fields.map((f) => (
              <Field key={f.key} label={f.label}>
                <input className="input" type="number" step={f.step ?? 1} min={0} value={form[f.key]} onChange={(e) => setNum(f.key, e.target.value)} />
              </Field>
            ))}
            {section.title === "Logistyka" && (
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={form.assume_available_without_entry}
                  onChange={(e) => setForm({ ...form, assume_available_without_entry: e.target.checked })}
                />
                Brak zgłoszenia dyspozycyjności = dostępny cały dzień
              </label>
            )}
          </div>
        ))}
        <div className="card p-6 md:col-span-2">
          <h2 className="mb-2 font-semibold tracking-tight">Kary za odległość</h2>
          <p className="mb-3 text-sm text-zinc-500">
            Próg „do X km” → kara. Ostatni próg obejmuje wszystkie większe odległości. Do kary progowej dodawane jest km × DISTANCE_WEIGHT.
          </p>
          <table className="table max-w-md">
            <thead>
              <tr>
                <th>Do (km)</th>
                <th>Kara (pkt)</th>
              </tr>
            </thead>
            <tbody>
              {form.distance_brackets.map(([upper, penalty], i) => (
                <tr key={i}>
                  <td>
                    {i === form.distance_brackets.length - 1 ? (
                      <span className="text-zinc-500">powyżej {form.distance_brackets[i - 1]?.[0] ?? 0}</span>
                    ) : (
                      <input className="input w-28" type="number" value={upper} onChange={(e) => setBracket(i, 0, e.target.value)} />
                    )}
                  </td>
                  <td>
                    <input className="input w-28" type="number" value={penalty} onChange={(e) => setBracket(i, 1, e.target.value)} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
