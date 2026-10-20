import { LICENSE_GROUPS } from "../types";

/** Przydzielanie licencji: klikalne pola pogrupowane wg rodzaju (można zaznaczyć kilka). */
export function LicensePicker({ value, onChange }: { value: string[]; onChange: (value: string[]) => void }) {
  const known = new Set(LICENSE_GROUPS.flatMap((g) => g.licenses));
  // Licencje spoza listy (np. ze starszych danych) zostają widoczne, żeby nie zginęły przy zapisie.
  const groups = [...LICENSE_GROUPS, { title: "Inne", licenses: value.filter((l) => !known.has(l)) }].filter((g) => g.licenses.length);
  const toggle = (license: string) => onChange(value.includes(license) ? value.filter((l) => l !== license) : [...value, license]);

  return (
    <div className="space-y-3">
      {groups.map((g) => (
        <div key={g.title}>
          <div className="mb-1 text-xs font-medium uppercase tracking-wide text-slate-500">{g.title}</div>
          <div className="flex flex-wrap gap-2">
            {g.licenses.map((l) => {
              const on = value.includes(l);
              return (
                <button
                  key={l}
                  type="button"
                  aria-pressed={on}
                  onClick={() => toggle(l)}
                  className={`rounded-full border px-3 py-1 text-xs font-medium transition ${
                    on ? "border-emerald-700 bg-emerald-700 text-white" : "border-slate-300 bg-white text-slate-700 hover:border-emerald-600"
                  }`}
                >
                  {on && "✓ "}
                  {l}
                </button>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}

/** Licencje sędziego w tabelach i kartach obsady. */
export function LicenseList({ licenses }: { licenses: string[] }) {
  if (!licenses.length) return <span className="text-slate-400">brak licencji</span>;
  return (
    <div className="flex flex-wrap gap-1">
      {licenses.map((l) => (
        <span key={l} className="rounded bg-emerald-50 px-1.5 py-0.5 text-xs text-emerald-800 ring-1 ring-emerald-200">
          {l}
        </span>
      ))}
    </div>
  );
}
