import { MapPin, Plus } from "lucide-react";
import { useState } from "react";

import { ErrorBanner, Loading, PageHeader } from "../components/Feedback";
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
      <div className="card overflow-hidden"><div className="overflow-x-auto">
        {venues.loading && !venues.data ? (
          <Loading />
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Nazwa</th>
                <th>Miasto</th>
                <th>Adres</th>
                <th className="text-right">Akcje</th>
              </tr>
            </thead>
            <tbody>
              {venues.data?.map((v) => (
                <tr key={v.id}>
                  <td>
                    <div className="flex items-center gap-3 font-medium">
                      <span className="flex size-8 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
                        <MapPin className="size-4" />
                      </span>
                      {v.name}
                    </div>
                  </td>
                  <td>{v.city}</td>
                  <td>{v.address}</td>
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
