import { Fragment, useState } from "react";

import { useAsync } from "../hooks/useAsync";
import { api } from "../services/api";
import type { RefereeRole } from "../types";
import { km, minutes, score } from "../utils/format";
import Explanation from "./Explanation";
import { ErrorBanner, Loading } from "./Feedback";
import Modal from "./Modal";

interface Props {
  matchId: number;
  role: RefereeRole;
  title: string;
  currentRefereeId?: number;
  onClose: () => void;
  onAssigned: (warning: string | null) => void;
}

/** Ranking sędziów dla meczu (najpierw możliwi wg SCORE, potem odrzuceni z powodem). */
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
              <th>Odległość</th>
              <th>Transport</th>
              <th>SCORE</th>
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
                  <td>{km(c.distance_km)}</td>
                  <td>{minutes(c.travel_minutes)}</td>
                  <td className="tabular-nums">{score(c.score)}</td>
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
                      <Explanation data={{ reasons: c.reasons, score_breakdown: c.score_breakdown }} total={c.score} />
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
