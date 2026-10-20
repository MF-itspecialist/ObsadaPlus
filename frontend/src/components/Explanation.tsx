import type { Explanation as ExplanationData } from "../types";

/** Uzasadnienie wyboru sędziego — lista powodów w zwykłym języku. */
export default function Explanation({ data }: { data: ExplanationData | null }) {
  if (!data) return <p className="text-sm text-slate-500">Brak uzasadnienia.</p>;
  return (
    <div className="space-y-2 text-sm">
      {data.rejection && <p className="font-medium text-red-600">✗ {data.rejection}</p>}
      {data.reasons.length > 0 && (
        <ul className="space-y-0.5">
          {data.reasons.map((r) => (
            <li key={r} className="text-slate-700">
              <span className="mr-1 text-emerald-600">✓</span>
              {r}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
