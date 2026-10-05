import { Link } from "react-router-dom";

import { ErrorBanner, Loading, PageHeader } from "../components/Feedback";
import StatCard from "../components/StatCard";
import { usePeriod } from "../context/PeriodContext";
import { useAsync } from "../hooks/useAsync";
import { api } from "../services/api";
import { dayName, formatDate } from "../utils/dates";
import { hhmm } from "../utils/format";

export default function DashboardPage() {
  const { period } = usePeriod();
  const stats = useAsync(() => api.dashboard(period), [period.date_from]);
  const matches = useAsync(() => api.matches(period), [period.date_from]);
  const s = stats.data;
  const unassigned = (matches.data ?? []).filter((m) => m.status === "UNASSIGNED" || m.status === "PARTIALLY_ASSIGNED");

  return (
    <div>
      <PageHeader title="Dashboard">
        <Link to="/assignments" className="btn-primary">
          Przejdź do obsady
        </Link>
      </PageHeader>
      <ErrorBanner message={stats.error} />
      {stats.loading && !s && <Loading />}
      {s && (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <StatCard label="Mecze weekendu" value={s.matches_total} />
          <StatCard label="Obsadzone" value={s.matches_assigned} tone="good" />
          <StatCard label="Nieobsadzone" value={s.matches_unassigned} tone={s.matches_unassigned ? "bad" : "default"} />
          <StatCard label="Dostępni sędziowie" value={s.available_referees} hint={`aktywnych: ${s.active_referees}`} />
          <StatCard label="Średnia liczba spotkań" value={s.avg_matches_per_referee.toFixed(2)} hint="na aktywnego sędziego" />
          <StatCard label="Łączny dystans" value={`${s.total_distance_km.toFixed(1)} km`} />
          <StatCard label="Średni dystans" value={`${s.avg_distance_km.toFixed(1)} km`} hint="na przypisanie" />
          <StatCard label="Konflikty" value={s.conflicts} tone={s.conflicts ? "bad" : "default"} hint="przypisania łamiące ograniczenia" />
        </div>
      )}

      <div className="card mt-6">
        <div className="border-b border-slate-200 px-4 py-3 font-semibold">Mecze bez pełnej obsady</div>
        {matches.loading && <Loading />}
        {!matches.loading && unassigned.length === 0 && <p className="px-4 py-6 text-sm text-slate-500">Wszystkie mecze weekendu są obsadzone.</p>}
        {unassigned.length > 0 && (
          <table className="table">
            <tbody>
              {unassigned.map((m) => (
                <tr key={m.id}>
                  <td className="whitespace-nowrap">
                    {dayName(m.date)}, {formatDate(m.date)}
                  </td>
                  <td>{hhmm(m.start_time)}</td>
                  <td>{m.league}</td>
                  <td>
                    {m.home_team} – {m.away_team}
                  </td>
                  <td>{m.venue.name}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
