import { ArrowLeft, FileText, Printer } from "lucide-react";
import { Link, useParams } from "react-router-dom";

import { ErrorBanner, Loading } from "../components/Feedback";
import { useAsync } from "../hooks/useAsync";
import { api } from "../services/api";
import { ROLE_LABELS, type PublishedRow } from "../types";
import { dayName, formatDate } from "../utils/dates";
import { groupBy } from "../utils/format";

/** Opublikowana wersja obsady — tylko do odczytu i do druku (bez menu aplikacji). */
export default function PublicationPage() {
  const { id } = useParams();
  const pub = useAsync(() => api.publication(Number(id)), [id]);

  if (pub.loading && !pub.data) return <Loading />;
  if (!pub.data)
    return (
      <div className="mx-auto max-w-5xl p-6">
        <ErrorBanner message={pub.error ?? "Nie znaleziono publikacji"} />
      </div>
    );

  const p = pub.data;
  const span = p.date_from === p.date_to ? formatDate(p.date_from) : `${formatDate(p.date_from)} – ${formatDate(p.date_to)}`;
  const when = new Date(p.published_at).toLocaleString("pl-PL", { dateStyle: "long", timeStyle: "short" });
  const days = groupBy(p.rows, (r) => r.date).sort(([a], [b]) => a.localeCompare(b));

  return (
    <div className="mx-auto max-w-5xl px-4 py-6 print:max-w-none print:p-0">
      <div className="mb-6 flex flex-wrap items-center gap-2 print:hidden">
        <Link className="btn-ghost" to="/assignments">
          <ArrowLeft className="size-4" /> Wróć do obsady
        </Link>
        <span className="flex-1" />
        <a className="btn-secondary" href={api.publicationPdfUrl(p.id)} download>
          <FileText className="size-4" /> Pobierz PDF
        </a>
        <button className="btn-primary" onClick={() => window.print()}>
          <Printer className="size-4" /> Drukuj
        </button>
      </div>

      <h1 className="text-2xl font-semibold tracking-tight text-zinc-900">Obsada sędziowska · {span}</h1>
      <p className="mt-1 text-sm text-zinc-500">
        Wersja {p.version}, opublikowana {when}
        {p.changed_matches.length > 0 && (
          <span className="text-amber-700 print:hidden"> · od publikacji zmieniono {p.changed_matches.length} mecz.</span>
        )}
      </p>

      {days.map(([day, rows]) => (
        <section key={day} className="mt-8 break-inside-avoid-page">
          <h2 className="mb-3 text-sm font-semibold tracking-wide text-zinc-900 uppercase">
            {dayName(day)} {formatDate(day)}
          </h2>
          <div className="card overflow-x-auto print:shadow-none">
            <table className="w-full table-fixed text-sm">
              <thead className="bg-zinc-50 text-left text-xs text-zinc-500">
                <tr>
                  <th className="w-20 px-4 py-2 font-medium">Godz.</th>
                  <th className="w-[32%] px-4 py-2 font-medium">Mecz</th>
                  <th className="w-[28%] px-4 py-2 font-medium">Obiekt</th>
                  <th className="px-4 py-2 font-medium">Obsada</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-100">
                {rows.map((r) => (
                  <PublishedMatch key={r.match_id} row={r} changed={p.changed_matches.includes(r.match_id)} />
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ))}
    </div>
  );
}

function PublishedMatch({ row, changed }: { row: PublishedRow; changed: boolean }) {
  return (
    <tr className={`align-top ${changed ? "bg-amber-50/60 print:bg-transparent" : ""}`}>
      <td className="px-4 py-3 font-semibold tabular-nums">{row.start_time}</td>
      <td className="px-4 py-3">
        <div className="font-medium">
          {row.home_team} – {row.away_team}
        </div>
        <div className="text-xs text-zinc-500">
          {row.league}
          {row.cancelled && <span className="ml-2 font-semibold text-red-600">ODWOŁANY</span>}
        </div>
      </td>
      <td className="px-4 py-3">
        <div>{row.venue_name}</div>
        {row.venue_address && <div className="text-xs text-zinc-500">{row.venue_address}</div>}
      </td>
      <td className="px-4 py-3">
        {row.crew.map((c) => (
          <div key={c.role}>
            <span className="text-xs text-zinc-500">{ROLE_LABELS[c.role]}: </span>
            {c.referee_name ? <span className="font-medium">{c.referee_name}</span> : <span className="font-medium text-red-600">brak</span>}
          </div>
        ))}
      </td>
    </tr>
  );
}
