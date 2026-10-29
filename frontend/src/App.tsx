import { Navigate, Route, Routes } from "react-router-dom";

import { Loading } from "./components/Feedback";
import Layout from "./components/Layout";
import { useAuth } from "./context/AuthContext";
import AssignmentsPage from "./pages/AssignmentsPage";
import AvailabilityPage from "./pages/AvailabilityPage";
import DashboardPage from "./pages/DashboardPage";
import LoginPage from "./pages/LoginPage";
import MatchesPage from "./pages/MatchesPage";
import PublicationPage from "./pages/PublicationPage";
import RefereeHomePage from "./pages/RefereeHomePage";
import RefereesPage from "./pages/RefereesPage";
import SettingsPage from "./pages/SettingsPage";
import ImportsPage from "./pages/ImportsPage";
import MapPage from "./pages/MapPage";
import StatisticsPage from "./pages/StatisticsPage";
import UsersPage from "./pages/UsersPage";
import VenuesPage from "./pages/VenuesPage";

export default function App() {
  const { user, checking } = useAuth();
  if (checking) return <Loading />;
  if (!user) return <LoginPage />;
  if (user.role === "REFEREE") return <RefereeHomePage />;
  return (
    <Routes>
      <Route path="publication/:id" element={<PublicationPage />} />
      <Route element={<Layout />}>
        <Route index element={<DashboardPage />} />
        <Route path="matches" element={<MatchesPage />} />
        <Route path="referees" element={<RefereesPage />} />
        <Route path="availability" element={<AvailabilityPage />} />
        <Route path="assignments" element={<AssignmentsPage />} />
        <Route path="venues" element={<VenuesPage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="users" element={<UsersPage />} />
        <Route path="statistics" element={<StatisticsPage />} />
        <Route path="map" element={<MapPage />} />
        <Route path="imports" element={<ImportsPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
