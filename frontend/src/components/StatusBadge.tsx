import { STATUS_LABELS, type MatchStatus } from "../types";

const STYLES: Record<MatchStatus, string> = {
  ASSIGNED: "bg-emerald-100 text-emerald-800",
  PARTIALLY_ASSIGNED: "bg-amber-100 text-amber-800",
  UNASSIGNED: "bg-red-100 text-red-700",
  CANCELLED: "bg-slate-200 text-slate-600",
};

export default function StatusBadge({ status }: { status: MatchStatus }) {
  return (
    <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${STYLES[status]}`}>
      {STATUS_LABELS[status]}
    </span>
  );
}

export function Tag({ children, tone = "slate" }: { children: React.ReactNode; tone?: "slate" | "amber" | "red" | "emerald" }) {
  const tones = {
    slate: "bg-slate-100 text-slate-700",
    amber: "bg-amber-100 text-amber-800",
    red: "bg-red-100 text-red-700",
    emerald: "bg-emerald-100 text-emerald-800",
  };
  return <span className={`inline-block rounded px-1.5 py-0.5 text-xs font-medium ${tones[tone]}`}>{children}</span>;
}
