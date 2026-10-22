import { useMemo } from "react";

import type { Referee } from "../types";
import { FilterRow, REGIONS, SearchBox, SelectFilter, matchesText, regionOptions, uniqueSorted } from "./Filters";

// Filtr sędziów: klasa rozgrywkowa, licencja, podokręg i dzielnica Warszawy (Sędziowie, Dyspozycyjność).

export interface RefereeFilter {
  query: string;
  cls: string;
  license: string;
  region: string;
  district: string;
}

export const EMPTY_REFEREE_FILTER: RefereeFilter = { query: "", cls: "", license: "", region: "", district: "" };

export function matchesRefereeFilter(r: Referee, f: RefereeFilter): boolean {
  return (
    (!f.cls || r.license_class === f.cls) &&
    (!f.license || r.licenses.includes(f.license)) &&
    (!f.region || r.region === f.region) &&
    (!f.district || r.district === f.district) &&
    matchesText([r.first_name, r.last_name, r.city, r.district, ...r.licenses], f.query)
  );
}

export default function RefereeFilters({ referees, filter, onChange, shown, withLicense = true }: {
  referees: Referee[];
  filter: RefereeFilter;
  onChange: (f: RefereeFilter) => void;
  shown: number;
  withLicense?: boolean;
}) {
  const classes = useMemo(
    () => [...new Map(referees.map((r) => [r.license_class, r.license_class_rank])).entries()].sort((a, b) => a[1] - b[1]).map(([c]) => c),
    [referees],
  );
  const licenses = useMemo(() => uniqueSorted(referees.flatMap((r) => r.licenses)), [referees]);
  const regions = useMemo(() => regionOptions(referees.map((r) => r.region)), [referees]);
  // Dzielnice mają tylko sędziowie z Warszawy.
  const districts = useMemo(() => uniqueSorted(referees.filter((r) => r.city === "Warszawa").map((r) => r.district)), [referees]);
  const set = (patch: Partial<RefereeFilter>) => onChange({ ...filter, ...patch });
  const active = Object.values(filter).some(Boolean);
  const showDistricts = !filter.region || filter.region === REGIONS[0];

  return (
    <FilterRow active={active} onClear={() => onChange(EMPTY_REFEREE_FILTER)} shown={shown} total={referees.length} noun="sędziów">
      <SearchBox value={filter.query} onChange={(query) => set({ query })} placeholder="Szukaj: imię, nazwisko, miejscowość" />
      <SelectFilter label="Klasa rozgrywkowa" all="Wszystkie klasy" options={classes} value={filter.cls} onChange={(cls) => set({ cls })} />
      {withLicense && <SelectFilter label="Licencja" all="Wszystkie licencje" options={licenses} value={filter.license} onChange={(license) => set({ license })} />}
      <SelectFilter
        label="Podokręg"
        all="Wszystkie podokręgi"
        options={regions}
        value={filter.region}
        onChange={(region) => set({ region, district: region && region !== REGIONS[0] ? "" : filter.district })}
      />
      {showDistricts && <SelectFilter label="Dzielnica Warszawy" all="Wszystkie dzielnice" options={districts} value={filter.district} onChange={(district) => set({ district })} />}
    </FilterRow>
  );
}
