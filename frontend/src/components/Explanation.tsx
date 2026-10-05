import type { Explanation as ExplanationData } from "../types";
import { SCORE_LABELS, score } from "../utils/format";

/** Uzasadnienie wyboru sędziego: lista ✓ i rozbicie SCORE. */
export default function Explanation({ data, total }: { data: ExplanationData | null; total?: number | null }) {
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
      {data.score_breakdown && (
        <table className="text-xs text-slate-600">
          <tbody>
            {Object.entries(data.score_breakdown).map(([k, v]) => (
              <tr key={k}>
                <td className="pr-4">{SCORE_LABELS[k] ?? k}</td>
                <td className="text-right tabular-nums">{score(v)}</td>
              </tr>
            ))}
            {total !== undefined && (
              <tr className="font-semibold text-slate-800">
                <td className="pr-4 pt-1">SCORE</td>
                <td className="pt-1 text-right tabular-nums">{score(total)}</td>
              </tr>
            )}
          </tbody>
        </table>
      )}
    </div>
  );
}
