import { Navigate, Route, Routes } from "react-router-dom";

import Layout from "./components/Layout";
import AssignmentsPage from "./pages/AssignmentsPage";
import AvailabilityPage from "./pages/AvailabilityPage";
import DashboardPage from "./pages/DashboardPage";
import MatchesPage from "./pages/MatchesPage";
import RefereesPage from "./pages/RefereesPage";
import SettingsPage from "./pages/SettingsPage";
import VenuesPage from "./pages/VenuesPage";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<DashboardPage />} />
        <Route path="matches" element={<MatchesPage />} />
        <Route path="referees" element={<RefereesPage />} />
        <Route path="availability" element={<AvailabilityPage />} />
        <Route path="assignments" element={<AssignmentsPage />} />
        <Route path="venues" element={<VenuesPage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
