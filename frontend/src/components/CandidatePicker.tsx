import { Fragment, useState } from "react";

import { useAsync } from "../hooks/useAsync";
import { api } from "../services/api";
import type { RefereeRole } from "../types";
import { km, minutes } from "../utils/format";
import Explanation from "./Explanation";
import { ErrorBanner, Loading } from "./Feedback";
import { LicenseList } from "./Licenses";
import Modal from "./Modal";

interface Props {
  matchId: number;
  role: RefereeRole;
  title: string;
  currentRefereeId?: number;
  onClose: () => void;
  onAssigned: (warning: string | null) => void;
}

/** Sędziowie dla meczu — od najlepiej pasującego; na końcu ci, którzy nie mogą, z powodem. */
export default function CandidatePicker({ matchId, role, title, currentRefereeId, onClose, onAssigned }: Props) {
  const { data, error, loading } = useAsync(() => api.candidates(matchId, role), [matchId, role]);
  const [expanded, setExpanded] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const choose = async (refereeId: number, feasible: boolean) => {
    if (!feasible && !confirm("Ten sędzia nie spełnia twardych ograniczeń. Przypisać mimo to?")) return;
    setSaving(true);
    try {
      const res = await api.assign(matchId, refereeId, role);
      onAssigned(res.warning);
    } catch (e) {
      setSaveError((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal title={title} onClose={onClose} wide>
      <ErrorBanner message={error ?? saveError} />
      {loading && <Loading />}
      {data && (
        <table className="table">
          <thead>
            <tr>
              <th>Sędzia</th>
              <th>Licencje</th>
              <th>Mieszka</th>
              <th>Dojazd</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {data.map((c) => (
              <Fragment key={c.referee_id}>
                <tr className={c.feasible ? "" : "text-slate-400"}>
                  <td>
                    <button className="text-left font-medium hover:underline" onClick={() => setExpanded(expanded === c.referee_id ? null : c.referee_id)}>
                      {c.referee_name}
                    </button>
                    {c.referee_id === currentRefereeId && <span className="ml-2 text-xs text-emerald-700">(obecny)</span>}
                    {!c.feasible && <div className="text-xs text-red-500">✗ {c.rejection}</div>}
                  </td>
                  <td className="max-w-56">
                    <LicenseList licenses={c.referee_licenses} />
                  </td>
                  <td>{c.referee_location}</td>
                  <td className="whitespace-nowrap">
                    {km(c.distance_km)}
                    {c.travel_minutes !== null && <span className="text-slate-400"> · {minutes(c.travel_minutes)}</span>}
                  </td>
                  <td className="text-right">
                    <button
                      className={c.feasible ? "btn-primary" : "btn-secondary"}
                      disabled={saving || c.referee_id === currentRefereeId}
                      onClick={() => choose(c.referee_id, c.feasible)}
                    >
                      Przypisz
                    </button>
                  </td>
                </tr>
                {expanded === c.referee_id && c.feasible && (
                  <tr>
                    <td colSpan={5} className="bg-slate-50">
                      <Explanation data={{ reasons: c.reasons }} />
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
          </tbody>
        </table>
      )}
    </Modal>
  );
}
