import { useEffect, useRef, useState } from "react";

import { ApiError, api } from "../services/api";
import { Field } from "./RefereeForm";

interface Props {
  address: string;
  city: string;
  onChange: (address: string, city: string) => void;
  /** Lokalizacja zapisana wcześniej (edycja) — pokazywana, dopóki adres się nie zmieni. */
  savedLabel?: string;
}

type Lookup = { state: "idle" } | { state: "searching" } | { state: "found"; label: string } | { state: "not_found" } | { state: "error" };

/** Adres + miasto. Lokalizacja (i dzielnica) jest wyszukiwana automatycznie w trakcie pisania. */
export default function AddressFields({ address, city, onChange, savedLabel }: Props) {
  const initial = useRef({ address, city });
  const [lookup, setLookup] = useState<Lookup>(savedLabel ? { state: "found", label: savedLabel } : { state: "idle" });

  useEffect(() => {
    const unchanged = address === initial.current.address && city === initial.current.city;
    if (unchanged && savedLabel) {
      setLookup({ state: "found", label: savedLabel });
      return;
    }
    if (!address.trim() && !city.trim()) {
      setLookup({ state: "idle" });
      return;
    }
    let cancelled = false;
    setLookup({ state: "searching" });
    const timer = setTimeout(async () => {
      try {
        const r = await api.geocode(address, city);
        if (!cancelled) setLookup({ state: "found", label: [r.city, r.district].filter(Boolean).join(", ") });
      } catch (e) {
        if (!cancelled) setLookup(e instanceof ApiError && e.status === 404 ? { state: "not_found" } : { state: "error" });
      }
    }, 700);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [address, city, savedLabel]);

  return (
    <div className="col-span-2">
      <div className="grid grid-cols-3 gap-3">
        <div className="col-span-2">
          <Field label="Adres (ulica i numer)">
            <input className="input" placeholder="np. ul. Puławska 100" value={address} onChange={(e) => onChange(e.target.value, city)} />
          </Field>
        </div>
        <Field label="Miasto">
          <input className="input" value={city} onChange={(e) => onChange(address, e.target.value)} />
        </Field>
      </div>
      <div className="mt-1 min-h-5 text-sm">
        {lookup.state === "searching" && <span className="text-zinc-500">Szukam adresu na mapie…</span>}
        {lookup.state === "found" && (
          <span className="text-emerald-600">
            ✓ Lokalizacja: <strong>{lookup.label}</strong>
          </span>
        )}
        {lookup.state === "not_found" && <span className="text-amber-700">Nie znaleziono tego adresu — sprawdź pisownię ulicy i miasta.</span>}
        {lookup.state === "error" && <span className="text-amber-700">Mapy są chwilowo niedostępne — lokalizacja zostanie sprawdzona przy zapisie.</span>}
      </div>
    </div>
  );
}
