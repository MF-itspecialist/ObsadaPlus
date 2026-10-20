import { STATUS_LABELS, type MatchStatus } from "../types";

const STYLES: Record<MatchStatus, { pill: string; dot: string }> = {
  ASSIGNED: { pill: "bg-emerald-50 text-emerald-700 ring-emerald-600/15", dot: "bg-emerald-500" },
  PARTIALLY_ASSIGNED: { pill: "bg-amber-50 text-amber-700 ring-amber-600/15", dot: "bg-amber-500" },
  UNASSIGNED: { pill: "bg-red-50 text-red-700 ring-red-600/15", dot: "bg-red-500" },
  CANCELLED: { pill: "bg-zinc-100 text-zinc-600 ring-zinc-500/15", dot: "bg-zinc-400" },
};

export default function StatusBadge({ status }: { status: MatchStatus }) {
  const s = STYLES[status];
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium whitespace-nowrap ring-1 ring-inset ${s.pill}`}>
      <span className={`size-1.5 rounded-full ${s.dot}`} />
      {STATUS_LABELS[status]}
    </span>
  );
}

type Tone = "slate" | "amber" | "red" | "emerald" | "brand";

const TAG_TONES: Record<Tone, string> = {
  slate: "bg-zinc-100 text-zinc-600 ring-zinc-500/10",
  amber: "bg-amber-50 text-amber-700 ring-amber-600/15",
  red: "bg-red-50 text-red-700 ring-red-600/15",
  emerald: "bg-emerald-50 text-emerald-700 ring-emerald-600/15",
  brand: "bg-brand-50 text-brand-700 ring-brand-600/15",
};

export function Tag({ children, tone = "slate" }: { children: React.ReactNode; tone?: Tone }) {
  return <span className={`inline-flex items-center rounded-md px-1.5 py-0.5 text-[11px] font-medium ring-1 ring-inset ${TAG_TONES[tone]}`}>{children}</span>;
}
