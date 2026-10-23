import { useEffect, useState } from "react";

import { ErrorBanner, InfoBanner, Loading, PageHeader } from "../components/Feedback";
import { Field } from "../components/RefereeForm";
import { useAsync } from "../hooks/useAsync";
import { api } from "../services/api";
import type { SystemSettings } from "../types";

type NumericKey = {
  [K in keyof SystemSettings]: SystemSettings[K] extends number ? K : never;
}[keyof SystemSettings];

type Section = { title: string; fields: { key: NumericKey; label: string; step?: number }[] };

const LOGISTICS: Section = {
  title: "Logistyka",
  fields: [
    { key: "arrival_before_minutes", label: "Przyjazd sędziego przed meczem (min)" },
    { key: "transport_safety_buffer_minutes", label: "Zapas czasu na dojazd (min)" },
    { key: "generator_max_matches_per_day", label: "Maks. meczów dziennie dla sędziego z automatu" },
    { key: "routing_avg_speed_kmh", label: "Średnia prędkość przejazdu (km/h)" },
    { key: "routing_road_factor", label: "Współczynnik krętości dróg", step: 0.05 },
    { key: "default_match_duration_minutes", label: "Domyślny czas meczu przy imporcie (min)" },
    { key: "mileage_rate", label: "Stawka kilometrówki (zł za km)", step: 0.0001 },
  ],
};

// Parametry algorytmu — dla zaawansowanych; domyślne wartości są dobrane do typowego weekendu.
const PRIORITIES: Section = {
  title: "Priorytety automatycznej obsady",
  fields: [
    { key: "distance_weight", label: "Jak mocno unikać długich dojazdów (km)", step: 0.1 },
    { key: "travel_time_weight", label: "Jak mocno unikać długiego czasu jazdy (min)", step: 0.1 },
    { key: "daily_match_weight", label: "Jak mocno unikać wielu meczów jednego dnia" },
    { key: "weekend_match_weight", label: "Jak mocno unikać wielu meczów w weekend" },
    { key: "workload_balance_weight", label: "Jak mocno wyrównywać liczbę meczów między sędziami" },
    { key: "crew_route_weight", label: "Jak mocno dobierać zespół G + A1 + A2, który dojedzie razem (km wspólnej trasy)", step: 0.1 },
    { key: "women_priority_penalty", label: "Jak mocno kierować sędzie z licencją kobiecą najpierw na mecze kobiet" },
    { key: "preferred_league_penalty", label: "Kara za mecz spoza preferowanych lig sędziego" },
    { key: "avoided_club_penalty", label: "Kara za mecz klubu, którego sędzia woli unikać" },
    { key: "within_preferred_factor", label: "Mnożnik w granicach preferencji sędziego", step: 0.05 },
    { key: "over_preferred_factor", label: "Mnożnik powyżej preferencji sędziego", step: 0.1 },
  ],
};

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
        <SectionCard section={LOGISTICS} form={form} setNum={setNum}>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={form.assume_available_without_entry}
              onChange={(e) => setForm({ ...form, assume_available_without_entry: e.target.checked })}
            />
            Brak zgłoszenia dyspozycyjności = dostępny cały dzień
          </label>
        </SectionCard>
      </div>
      <details className="mt-6">
        <summary className="cursor-pointer text-sm font-semibold text-zinc-700">Ustawienia zaawansowane (algorytm obsady)</summary>
        <p className="mt-2 text-sm text-zinc-500">Zwykle nie trzeba ich zmieniać. Wyższa wartość = algorytm bardziej unika danej sytuacji.</p>
        <div className="mt-3 grid gap-4 md:grid-cols-2">
          <SectionCard section={PRIORITIES} form={form} setNum={setNum} />
          <div className="card p-6">
            <h2 className="mb-2 font-semibold tracking-tight">Unikanie dalekich dojazdów</h2>
            <p className="mb-3 text-sm text-zinc-500">
              Im dalej sędzia ma na mecz, tym mniej chętnie algorytm go wybiera. Ostatni próg obejmuje wszystkie większe odległości.
            </p>
            <table className="table max-w-md">
              <thead>
                <tr>
                  <th>Do (km)</th>
                  <th>Kara</th>
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
      </details>
    </div>
  );
}

function SectionCard({
  section,
  form,
  setNum,
  children,
}: {
  section: Section;
  form: SystemSettings;
  setNum: (k: NumericKey, v: string) => void;
  children?: React.ReactNode;
}) {
  return (
    <div className="card space-y-4 p-6">
      <h2 className="font-semibold tracking-tight">{section.title}</h2>
      {section.fields.map((f) => (
        <Field key={f.key} label={f.label}>
          <input className="input" type="number" step={f.step ?? 1} min={0} value={form[f.key]} onChange={(e) => setNum(f.key, e.target.value)} />
        </Field>
      ))}
      {children}
    </div>
  );
}
