const PALETTE = [
  "bg-brand-100 text-brand-700",
  "bg-emerald-100 text-emerald-700",
  "bg-amber-100 text-amber-800",
  "bg-sky-100 text-sky-700",
  "bg-rose-100 text-rose-700",
  "bg-violet-100 text-violet-700",
  "bg-teal-100 text-teal-700",
];

/** Inicjały sędziego w kolorowym kółku (kolor stały dla danego nazwiska). */
export default function Avatar({ name, size = "md", muted }: { name: string; size?: "sm" | "md"; muted?: boolean }) {
  const initials = name
    .split(" ")
    .filter(Boolean)
    .map((p) => p[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
  const hash = [...name].reduce((h, c) => h + c.charCodeAt(0), 0);
  const color = muted ? "bg-zinc-100 text-zinc-400" : PALETTE[hash % PALETTE.length];
  const dims = size === "sm" ? "size-7 text-[11px]" : "size-9 text-xs";
  return <span className={`inline-flex shrink-0 items-center justify-center rounded-full font-semibold ${dims} ${color}`}>{initials}</span>;
}
