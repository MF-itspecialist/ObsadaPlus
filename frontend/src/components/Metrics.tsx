import { Car, MapPin } from "lucide-react";

/** Kolor odległości: zielony do 10 km, bursztynowy do 30 km, czerwony powyżej. */
export function distanceTone(km: number | null | undefined): string {
  if (km === null || km === undefined) return "text-zinc-400";
  if (km < 10) return "text-emerald-600";
  if (km < 30) return "text-amber-600";
  return "text-red-600";
}

/** Odległość i czas dojazdu sędziego na mecz. */
export function MetricChips({ distance, travel }: { distance: number | null; travel: number | null }) {
  return (
    <div className="flex flex-wrap items-center gap-2 text-xs">
      <span className={`inline-flex items-center gap-1 rounded-lg bg-zinc-50 px-2 py-1 font-medium ring-1 ring-zinc-950/5 ring-inset ${distanceTone(distance)}`}>
        <MapPin className="size-3.5" />
        {distance === null ? "—" : `${distance.toFixed(1)} km`}
      </span>
      <span className="inline-flex items-center gap-1 rounded-lg bg-zinc-50 px-2 py-1 font-medium text-zinc-600 ring-1 ring-zinc-950/5 ring-inset">
        <Car className="size-3.5" />
        {travel === null ? "—" : `${Math.round(travel)} min`}
      </span>
    </div>
  );
}
