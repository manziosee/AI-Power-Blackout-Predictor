import { Link } from "react-router-dom";
import { useGeolocation } from "../hooks/useGeolocation";
import { usePredictions } from "../hooks/usePredictions";
import PredictionCard from "../components/Dashboard/PredictionCard";
import OutageHistory from "../components/Dashboard/OutageHistory";

export default function Dashboard() {
  const { h3Index } = useGeolocation();
  const predictions = usePredictions(h3Index ?? "");

  return (
    <div className="min-h-screen bg-slate-900 p-4 max-w-md mx-auto flex flex-col gap-4">
      <header className="flex items-center gap-3 pt-4">
        <Link to="/" className="text-slate-400 hover:text-white">←</Link>
        <h1 className="text-xl font-bold">Dashboard</h1>
      </header>

      <section>
        <p className="text-slate-400 text-xs uppercase tracking-widest mb-2">Next 24h Predictions</p>
        <div className="flex flex-col gap-3">
          {predictions.slice(0, 6).map((p) => (
            <PredictionCard key={p.id} prediction={p} />
          ))}
          {!predictions.length && (
            <p className="text-slate-500 text-sm text-center py-8">No predictions available yet.</p>
          )}
        </div>
      </section>

      {h3Index && (
        <section>
          <p className="text-slate-400 text-xs uppercase tracking-widest mb-2">Outage History</p>
          <OutageHistory h3_index={h3Index} />
        </section>
      )}
    </div>
  );
}
