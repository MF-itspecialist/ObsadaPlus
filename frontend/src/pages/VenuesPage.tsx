import { ExternalLink, MapPin, Plus } from "lucide-react";
import { useMemo, useState } from "react";

import { ErrorBanner, Loading, PageHeader } from "../components/Feedback";
import { FilterRow, SearchBox, SelectFilter, matchesText, regionOptions, uniqueSorted } from "../components/Filters";
import Modal from "../components/Modal";
import RowActions from "../components/RowActions";
import VenueForm from "../components/VenueForm";
import { useAsync } from "../hooks/useAsync";
import { api } from "../services/api";
import type { Venue, VenueInput } from "../types";

export default function VenuesPage() {
  const venues = useAsync(() => api.venues(), []);
  const [editing, setEditing] = useState<Venue | "new" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState({ query: "", region: "", city: "" });
  const all = useMemo(() => venues.data ?? [], [venues.data]);
  const rows = all.filter(
    (v) =>
      (!filter.region || v.region === filter.region) &&
      (!filter.city || v.city === filter.city) &&
      matchesText([v.name, v.city, v.address, v.postal_code], filter.query),
  );
  const regions = useMemo(() => regionOptions(all.map((v) => v.region)), [all]);
  const cities = useMemo(() => uniqueSorted(all.filter((v) => !filter.region || v.region === filter.region).map((v) => v.city)), [all, filter.region]);
  const missing = all.filter((v) => !v.postal_code).length;

  const save = async (data: VenueInput) => {
    if (editing === "new") await api.createVenue(data);
    else if (editing) await api.updateVenue(editing.id, data);
    setEditing(null);
    venues.reload();
  };

  const remove = async (v: Venue) => {
    if (!confirm(`Usunąć obiekt ${v.name}?`)) return;
    try {
      await api.deleteVenue(v.id);
      venues.reload();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  return (
    <div>
      <PageHeader title="Obiekty" subtitle="Stadiony i boiska z lokalizacją używaną do liczenia dojazdu">
        <button className="btn-primary" onClick={() => setEditing("new")}>
          <Plus className="size-4" /> Dodaj obiekt
        </button>
      </PageHeader>
      <ErrorBanner message={error ?? venues.error} onClose={() => setError(null)} />
      <FilterRow active={!!(filter.query || filter.region || filter.city)} onClear={() => setFilter({ query: "", region: "", city: "" })} shown={rows.length} total={all.length} noun="obiektów">
        <SearchBox value={filter.query} onChange={(query) => setFilter({ ...filter, query })} placeholder="Szukaj: nazwa, ulica, kod pocztowy" />
        <SelectFilter label="Podokręg" all="Wszystkie podokręgi" options={regions} value={filter.region} onChange={(region) => setFilter({ ...filter, region, city: "" })} />
        <SelectFilter label="Miejscowość" all="Wszystkie miejscowości" options={cities} value={filter.city} onChange={(city) => setFilter({ ...filter, city })} />
        {missing > 0 && <span className="text-sm text-amber-700">{missing} bez kodu pocztowego</span>}
      </FilterRow>
      <div className="card overflow-hidden"><div className="overflow-x-auto">
        {venues.loading && !venues.data ? (
          <Loading />
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Nazwa</th>
                <th>Adres</th>
                <th>Kod pocztowy</th>
                <th>Miejscowość</th>
                <th>Podokręg</th>
                <th>Mapa</th>
                <th className="text-right">Akcje</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((v) => (
                <tr key={v.id}>
                  <td>
                    <div className="flex items-center gap-3 font-medium">
                      <span className="flex size-8 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
                        <MapPin className="size-4" />
                      </span>
                      {v.name}
                    </div>
                  </td>
                  <td>{v.address || <span className="text-zinc-400">—</span>}</td>
                  <td className="tabular-nums whitespace-nowrap">{v.postal_code || <span className="text-zinc-400">—</span>}</td>
                  <td>{v.city}</td>
                  <td>{v.region}</td>
                  <td>
                    <a
                      className="btn-link"
                      href={`https://www.openstreetmap.org/?mlat=${v.latitude}&mlon=${v.longitude}#map=17/${v.latitude}/${v.longitude}`}
                      target="_blank"
                      rel="noreferrer"
                    >
                      <ExternalLink className="size-3.5" /> pokaż
                    </a>
                  </td>
                  <td className="whitespace-nowrap">
                    <RowActions onEdit={() => setEditing(v)} onDelete={() => remove(v)} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div></div>
      {editing && (
        <Modal title={editing === "new" ? "Nowy obiekt" : "Edycja obiektu"} onClose={() => setEditing(null)}>
          <VenueForm initial={editing === "new" ? undefined : editing} onSubmit={save} onCancel={() => setEditing(null)} />
        </Modal>
      )}
    </div>
  );
}
