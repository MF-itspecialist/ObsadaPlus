import { useAsync } from "../hooks/useAsync";
import { api } from "../services/api";
import type { LicenseGroup } from "../types";
import { Loading } from "./Feedback";

/** Przydzielanie licencji: klikalne pola pogrupowane wg rodzaju (można zaznaczyć kilka). Lista i uprawnienia pochodzą z backendu. */
export function LicensePicker({ value, onChange }: { value: string[]; onChange: (value: string[]) => void }) {
  const catalog = useAsync(() => api.licenses(), []);
  if (!catalog.data) return <Loading />;
  const known = new Set(catalog.data.flatMap((g) => g.licenses.map((l) => l.name)));
  // Licencje spoza listy (np. ze starszych danych) zostają widoczne, żeby nie zginęły przy zapisie.
  const other: LicenseGroup = { title: "Inne", licenses: value.filter((l) => !known.has(l)).map((name) => ({ name, scope: "", assumption: null })) };
  const groups = [...catalog.data, other].filter((g) => g.licenses.length);
  const toggle = (license: string) => onChange(value.includes(license) ? value.filter((l) => l !== license) : [...value, license]);

  return (
    <div className="space-y-3">
      {groups.map((g) => (
        <div key={g.title}>
          <div className="mb-1 text-xs font-medium text-zinc-500">{g.title}</div>
          <div className="flex flex-wrap gap-2">
            {g.licenses.map((l) => {
              const on = value.includes(l.name);
              const hint = [l.scope, l.assumption && `założenie do weryfikacji: ${l.assumption}`].filter(Boolean).join(" · ");
              return (
                <button
                  key={l.name}
                  type="button"
                  aria-pressed={on}
                  title={hint}
                  onClick={() => toggle(l.name)}
                  className={`rounded-full border px-3 py-1 text-xs font-medium transition ${
                    on ? "border-brand-600 bg-brand-600 text-white" : "border-zinc-300 bg-white text-zinc-700 hover:border-brand-500"
                  }`}
                >
                  {on && "✓ "}
                  {l.name}
                  {l.assumption && <span className="ml-0.5 opacity-60">*</span>}
                </button>
              );
            })}
          </div>
        </div>
      ))}
      <p className="text-xs text-zinc-500">Najedź na licencję, aby zobaczyć uprawnienia. * — zasada do potwierdzenia z Komisją Sędziowską.</p>
    </div>
  );
}

/** Licencje sędziego w tabelach i kartach obsady. */
export function LicenseList({ licenses }: { licenses: string[] }) {
  if (!licenses.length) return <span className="text-xs text-zinc-400">brak licencji</span>;
  return (
    <div className="flex flex-wrap gap-1">
      {licenses.map((l) => (
        <span key={l} className="rounded-md bg-brand-50 px-1.5 py-0.5 text-xs text-brand-700 ring-1 ring-brand-600/10 ring-inset">
          {l}
        </span>
      ))}
    </div>
  );
}
