/** "14:00:00" → "14:00" */
export function hhmm(value: string | null | undefined): string {
  return value ? value.slice(0, 5) : "—";
}

export function km(value: number | null | undefined): string {
  return value === null || value === undefined ? "—" : `${value.toFixed(1)} km`;
}

export function minutes(value: number | null | undefined): string {
  return value === null || value === undefined ? "—" : `${Math.round(value)} min`;
}

export function groupBy<T>(items: T[], key: (item: T) => string): [string, T[]][] {
  const map = new Map<string, T[]>();
  items.forEach((item) => {
    const k = key(item);
    map.set(k, [...(map.get(k) ?? []), item]);
  });
  return [...map.entries()];
}
