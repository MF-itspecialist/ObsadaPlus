import { Check, X } from "lucide-react";

import type { Explanation as ExplanationData } from "../types";

/** Uzasadnienie wyboru sędziego — lista powodów w zwykłym języku. */
export default function Explanation({ data }: { data: ExplanationData | null }) {
  if (!data) return <p className="text-sm text-zinc-500">Brak uzasadnienia.</p>;
  return (
    <div className="space-y-1.5 text-sm">
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
  );
}
