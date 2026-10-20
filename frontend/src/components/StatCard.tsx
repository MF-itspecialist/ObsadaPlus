import type { LucideIcon } from "lucide-react";

interface Props {
  label: string;
  value: string | number;
  hint?: string;
  icon?: LucideIcon;
  tone?: "default" | "good" | "bad" | "brand";
}

const ICON_TONES = {
  default: "bg-zinc-100 text-zinc-600",
  brand: "bg-brand-50 text-brand-600",
  good: "bg-emerald-50 text-emerald-600",
  bad: "bg-red-50 text-red-600",
};

export default function StatCard({ label, value, hint, icon: Icon, tone = "default" }: Props) {
  return (
    <div className="card p-5">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-zinc-500">{label}</span>
        {Icon && (
          <span className={`flex size-8 items-center justify-center rounded-lg ${ICON_TONES[tone]}`}>
            <Icon className="size-4" />
          </span>
        )}
      </div>
      <div className="mt-3 text-3xl font-semibold tracking-tight tabular-nums">{value}</div>
      {hint && <div className="mt-1 text-xs text-zinc-500">{hint}</div>}
    </div>
  );
}
