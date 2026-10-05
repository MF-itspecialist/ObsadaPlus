interface Props {
  label: string;
  value: string | number;
  hint?: string;
  tone?: "default" | "good" | "bad";
}

const TONES = {
  default: "text-slate-900",
  good: "text-emerald-700",
  bad: "text-red-600",
};

export default function StatCard({ label, value, hint, tone = "default" }: Props) {
  return (
    <div className="card p-4">
      <div className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</div>
      <div className={`mt-1 text-3xl font-semibold tabular-nums ${TONES[tone]}`}>{value}</div>
      {hint && <div className="mt-1 text-xs text-slate-500">{hint}</div>}
    </div>
  );
}
