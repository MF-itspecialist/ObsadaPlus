import { ChevronDown, RefreshCw } from "lucide-react";
import { Fragment, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { EmptyState, ErrorBanner, InfoBanner, Loading, PageHeader } from "../components/Feedback";
import { Field } from "../components/RefereeForm";
import { Tag } from "../components/StatusBadge";
import { useAsync } from "../hooks/useAsync";
import { api } from "../services/api";
import type { ImportRun, SystemSettings } from "../types";
import { shortDay } from "../utils/dates";

function when(iso: string): string {
  return new Date(iso).toLocaleString("pl-PL", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
}

/** Automatyczna aktualizacja meczów z 90minut.pl: ustawienia, „Uruchom teraz” i historia. */
export default function ImportsPage() {
  const runs = useAsync(() => api.importRuns(), []);
  const loaded = useAsync(() => api.settings(), []);
  const [form, setForm] = useState<SystemSettings | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [open, setOpen] = useState<number | null>(null);
  const running = (runs.data ?? []).some((r) => r.status === "running");

  useEffect(() => {
    if (loaded.data) setForm(loaded.data);
  }, [loaded.data]);

  // Odśwież historię, dopóki import trwa.
  useEffect(() => {
    if (!running) return;
    const t = setTimeout(() => runs.reload(), 3000);
    return () => clearTimeout(t);
  }, [running, runs.data]); // eslint-disable-line react-hooks/exhaustive-deps

  const save = async () => {
    if (!form) return;
    try {
      setForm(await api.saveSettings(form));
      setInfo("Zapisano.");
    } catch (e) {
      setError((e as Error).message);
    }
  };
  const runNow = async () => {
    try {
      await api.runImport();
      runs.reload();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  return (
    <div className="max-w-5xl">
      <PageHeader title="Aktualizacje meczów" subtitle="Codzienny import terminarza seniorów z 90minut.pl i zmiany w obsadzonych meczach">
        <button className="btn-primary" onClick={runNow} disabled={running}>
          <RefreshCw className={`size-4 ${running ? "animate-spin" : ""}`} /> {running ? "Import trwa…" : "Uruchom teraz"}
        </button>
      </PageHeader>
      <ErrorBanner message={error ?? runs.error} onClose={() => setError(null)} />
      <InfoBanner message={info} onClose={() => setInfo(null)} />

      {form && (
        <div className="card mb-6 p-6">
          <label className="flex items-center gap-2 text-sm font-medium">
            <input type="checkbox" checked={form.auto_import_enabled} onChange={(e) => setForm({ ...form, auto_import_enabled: e.target.checked })} />
            Codziennie aktualizuj mecze automatycznie
          </label>
          <div className="mt-4 grid gap-3 sm:grid-cols-4">
            <Field label="Godzina importu">
              <select className="input" value={form.auto_import_hour} onChange={(e) => setForm({ ...form, auto_import_hour: Number(e.target.value) })}>
                {Array.from({ length: 24 }, (_, h) => (
                  <option key={h} value={h}>
                    {String(h).padStart(2, "0")}:00
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Sezon (id_sezon w 90minut)">
              <input type="number" className="input" value={form.m90_season_id} onChange={(e) => setForm({ ...form, m90_season_id: Number(e.target.value) })} />
            </Field>
            <Field label="Okręg (id_okreg)">
              <input type="number" className="input" value={form.m90_region_id} onChange={(e) => setForm({ ...form, m90_region_id: Number(e.target.value) })} />
            </Field>
            <div className="flex items-end">
              <button className="btn-secondary w-full" onClick={save}>
                Zapisz
              </button>
            </div>
          </div>
          <p className="mt-3 text-xs text-zinc-500">
            Importowane są mecze od dziś: nowe są dodawane, a zmienione terminy aktualizowane. Juniorów z Łączy Nas Piłka dalej importuje się ręcznie.
            Sezon 2026/27 to id 109; na nowy sezon wpisz id z adresu strony okręgu w 90minut.pl.
          </p>
        </div>
      )}

      {runs.loading && !runs.data ? (
        <Loading />
      ) : !runs.data?.length ? (
        <EmptyState title="Jeszcze nie było importu" hint="Pierwszy uruchomi się o ustawionej godzinie albo po kliknięciu „Uruchom teraz”." />
      ) : (
        <div className="card overflow-hidden">
          <table className="table">
            <thead>
              <tr>
                <th>Kiedy</th>
                <th>Rodzaj</th>
                <th className="text-right">Nowe</th>
                <th className="text-right">Zaktualizowane</th>
                <th>Zmiany w obsadzonych</th>
              </tr>
            </thead>
            <tbody>
              {runs.data.map((r) => (
                <RunRow key={r.id} r={r} open={open === r.id} onToggle={() => setOpen(open === r.id ? null : r.id)} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function RunRow({ r, open, onToggle }: { r: ImportRun; open: boolean; onToggle: () => void }) {
  const details = r.changes.length > 0 || r.messages.length > 0;
  return (
    <Fragment>
      <tr className={details ? "cursor-pointer" : ""} onClick={details ? onToggle : undefined}>
        <td className="whitespace-nowrap tabular-nums">
          <div className="flex items-center gap-2">
            {details && <ChevronDown className={`size-4 text-zinc-400 transition ${open ? "rotate-180" : ""}`} />}
            {when(r.started_at)}
          </div>
        </td>
        <td>
          {r.status === "running" ? <Tag tone="brand">trwa</Tag> : r.status === "error" ? <Tag tone="red">błąd</Tag> : null}{" "}
          <span className="text-sm text-zinc-500">{r.trigger === "auto" ? "automatyczny" : "ręczny"}</span>
        </td>
        <td className="text-right tabular-nums">{r.created}</td>
        <td className="text-right tabular-nums">{r.updated}</td>
        <td>{r.changes.length ? <Tag tone="amber">{r.changes.length} do sprawdzenia</Tag> : <span className="text-zinc-400">—</span>}</td>
      </tr>
      {open && (
        <tr>
          <td colSpan={5} className="bg-zinc-50">
            {r.changes.length > 0 && (
              <ul className="mb-2 space-y-1.5 text-sm">
                {r.changes.map((c) => (
                  <li key={c.match_id}>
                    <span className="tabular-nums text-zinc-500">{shortDay(c.date)}</span> <span className="font-medium">{c.label}</span>: {c.what}
                    <span className="text-zinc-500"> · obsada: {c.referees.join(", ")}</span>{" "}
                    <Link className="text-brand-600 hover:underline" to="/assignments">
                      sprawdź
                    </Link>
                  </li>
                ))}
              </ul>
            )}
            {r.messages.map((m, i) => (
              <div key={i} className="text-xs text-zinc-500">
                {m}
              </div>
            ))}
          </td>
        </tr>
      )}
    </Fragment>
  );
}
