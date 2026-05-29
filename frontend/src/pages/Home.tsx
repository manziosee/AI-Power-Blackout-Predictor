import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useGeolocation } from "../hooks/useGeolocation";
import { usePredictions } from "../hooks/usePredictions";
import AlertBanner from "../components/Alerts/AlertBanner";
import PredictionCard from "../components/Dashboard/PredictionCard";
import LanguageSwitcher from "../components/common/LanguageSwitcher";
import { useOfflineSync } from "../hooks/useOfflineSync";

export default function Home() {
  const { t } = useTranslation();
  const { h3Index } = useGeolocation();
  const predictions = usePredictions(h3Index ?? "");
  useOfflineSync();

  const latest = predictions[0] ?? null;

  return (
    <div className="min-h-screen bg-slate-900 p-4 flex flex-col gap-4 max-w-md mx-auto">
      <header className="flex justify-between items-center pt-4">
        <div>
          <h1 className="text-xl font-bold text-white">⚡ Blackout Predictor</h1>
          <p className="text-slate-400 text-xs">AI-powered outage alerts</p>
        </div>
        <LanguageSwitcher />
      </header>

      <AlertBanner prediction={latest} />

      {latest ? (
        <PredictionCard prediction={latest} />
      ) : (
        <div className="bg-slate-800 rounded-2xl p-8 text-center text-slate-500">
          <p className="text-4xl mb-2">📍</p>
          <p>{h3Index ? "Loading predictions..." : "Allow location to see your area's risk"}</p>
        </div>
      )}

      <div className="grid grid-cols-2 gap-3">
        <Link to="/map" className="bg-blue-600 hover:bg-blue-700 rounded-xl p-4 text-center font-semibold transition-colors">
          🗺 View Map
        </Link>
        <Link to="/report" className="bg-red-600 hover:bg-red-700 rounded-xl p-4 text-center font-semibold transition-colors">
          ⚡ Report Outage
        </Link>
        <Link to="/dashboard" className="bg-slate-700 hover:bg-slate-600 rounded-xl p-4 text-center font-semibold transition-colors">
          📊 Dashboard
        </Link>
        <Link to="/alerts" className="bg-slate-700 hover:bg-slate-600 rounded-xl p-4 text-center font-semibold transition-colors">
          🔔 Alerts
        </Link>
      </div>
    </div>
  );
}
