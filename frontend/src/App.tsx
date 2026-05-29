import { Routes, Route } from "react-router-dom";
import Home from "./pages/Home";
import Dashboard from "./pages/Dashboard";
import MapPage from "./pages/Map";
import AlertSettingsPage from "./pages/AlertSettings";
import ReportOutagePage from "./pages/ReportOutage";
import ProfilePage from "./pages/Profile";
import OfflineBadge from "./components/common/OfflineBadge";

export default function App() {
  return (
    <div className="min-h-screen">
      <OfflineBadge />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/map" element={<MapPage />} />
        <Route path="/alerts" element={<AlertSettingsPage />} />
        <Route path="/report" element={<ReportOutagePage />} />
        <Route path="/profile" element={<ProfilePage />} />
      </Routes>
    </div>
  );
}
