// Operacje na datach w formacie ISO (YYYY-MM-DD) bez stref czasowych.

export function toIso(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

export function fromIso(iso: string): Date {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d);
}

export function addDays(iso: string, days: number): string {
  const d = fromIso(iso);
  d.setDate(d.getDate() + days);
  return toIso(d);
}

/**
 * Sobota "kolejki", do której należy dzień (zgodnie z backendem: wtorek–sobota → najbliższa
 * sobota, niedziela i poniedziałek → poprzednia sobota). Dni obsadowe to piątek–poniedziałek.
 */
export function saturdayOf(iso: string): string {
  const d = fromIso(iso);
  const dow = d.getDay(); // 0 = niedziela, 1 = poniedziałek, 6 = sobota
  const diff = dow === 0 ? -1 : dow === 1 ? -2 : 6 - dow;
  d.setDate(d.getDate() + diff);
  return toIso(d);
}

/** Sobota najbliższych dni obsadowych; w poniedziałek planujemy już kolejny weekend. */
export function upcomingSaturday(today: Date = new Date()): string {
  const iso = toIso(today);
  return today.getDay() === 1 ? addDays(saturdayOf(iso), 7) : saturdayOf(iso);
}

const DAY_NAMES = ["niedziela", "poniedziałek", "wtorek", "środa", "czwartek", "piątek", "sobota"];

export function dayName(iso: string): string {
  return DAY_NAMES[fromIso(iso).getDay()];
}

export function formatDate(iso: string): string {
  const d = fromIso(iso);
  return `${String(d.getDate()).padStart(2, "0")}.${String(d.getMonth() + 1).padStart(2, "0")}.${d.getFullYear()}`;
}

export function datesBetween(from: string, to: string): string[] {
  const out: string[] = [];
  for (let d = from; d <= to; d = addDays(d, 1)) out.push(d);
  return out;
}
