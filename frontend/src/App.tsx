import { Routes, Route } from "react-router-dom";
import Home from "./pages/Home";
import Dashboard from "./pages/Dashboard";
import MapPage from "./pages/Map";
import AlertSettingsPage from "./pages/AlertSettings";
import ReportOutagePage from "./pages/ReportOutage";
import ProfilePage from "./pages/Profile";
import AnalyticsPage from "./pages/Analytics";
import CommunityPage from "./pages/Community";
import EnterprisePage from "./pages/Enterprise";
import AdminDashboard from "./pages/AdminDashboard";
import LocationsPage from "./pages/Locations";
import Login from "./pages/Login";
import Register from "./pages/Register";
import OfflineBadge from "./components/common/OfflineBadge";
import ProtectedRoute from "./components/common/ProtectedRoute";

export default function App() {
  return (
    <div className="min-h-screen">
      <OfflineBadge />
      <Routes>
        {/* Public */}
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />

        {/* Protected */}
        <Route path="/" element={<ProtectedRoute><Home /></ProtectedRoute>} />
        <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
        <Route path="/map" element={<ProtectedRoute><MapPage /></ProtectedRoute>} />
        <Route path="/alerts" element={<ProtectedRoute><AlertSettingsPage /></ProtectedRoute>} />
        <Route path="/report" element={<ProtectedRoute><ReportOutagePage /></ProtectedRoute>} />
        <Route path="/profile" element={<ProtectedRoute><ProfilePage /></ProtectedRoute>} />
        <Route path="/analytics" element={<ProtectedRoute><AnalyticsPage /></ProtectedRoute>} />
        <Route path="/community" element={<ProtectedRoute><CommunityPage /></ProtectedRoute>} />
        <Route path="/enterprise" element={<ProtectedRoute><EnterprisePage /></ProtectedRoute>} />
        <Route path="/locations" element={<ProtectedRoute><LocationsPage /></ProtectedRoute>} />
        <Route path="/admin" element={<ProtectedRoute><AdminDashboard /></ProtectedRoute>} />
      </Routes>
    </div>
  );
}
