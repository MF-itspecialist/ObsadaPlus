import { Check, X } from "lucide-react";

import type { Explanation as ExplanationData } from "../types";
import { SCORE_LABELS, score } from "../utils/format";

/** Uzasadnienie wyboru sędziego: lista ✓ i rozbicie SCORE z paskami udziału. */
export default function Explanation({ data, total }: { data: ExplanationData | null; total?: number | null }) {
  if (!data) return <p className="text-sm text-zinc-500">Brak uzasadnienia.</p>;
  const entries = Object.entries(data.score_breakdown ?? {});
  const max = Math.max(1, ...entries.map(([, v]) => v));
  return (
    <div className="grid gap-5 text-sm md:grid-cols-2">
      <div className="space-y-1.5">
        {data.rejection && (
          <p className="flex items-start gap-2 font-medium text-red-600">
            <X className="mt-0.5 size-4 shrink-0" /> {data.rejection}
          </p>
        )}
        {data.reasons.map((r) => (
          <p key={r} className="flex items-start gap-2 text-zinc-700">
            <Check className="mt-0.5 size-4 shrink-0 text-emerald-500" />
            {r}
          </p>
        ))}
      </div>
      {entries.length > 0 && (
        <div className="space-y-2">
          {entries.map(([k, v]) => (
            <div key={k}>
              <div className="flex justify-between text-xs text-zinc-500">
                <span>{SCORE_LABELS[k] ?? k}</span>
                <span className="tabular-nums">{score(v)}</span>
              </div>
              <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-zinc-100">
                <div className="h-full rounded-full bg-brand-500" style={{ width: `${(v / max) * 100}%` }} />
              </div>
            </div>
          ))}
          {total !== undefined && (
            <div className="flex justify-between border-t border-zinc-200 pt-2 text-sm font-semibold">
              <span>SCORE</span>
              <span className="tabular-nums">{score(total)}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
