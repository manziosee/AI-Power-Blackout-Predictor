import { Link } from "react-router-dom";
import { useHeatmap } from "../hooks/usePredictions";

const RISK_COLORS: Record<string, string> = {
  low: "#22c55e",
  medium: "#f59e0b",
  high: "#ef4444",
  critical: "#7c3aed",
};

export default function MapPage() {
  const heatmap = useHeatmap("RW");

  return (
    <div className="min-h-screen bg-slate-900 flex flex-col">
      <header className="flex items-center gap-3 p-4">
        <Link to="/" className="text-slate-400 hover:text-white">←</Link>
        <h1 className="text-xl font-bold">Global Heatmap</h1>
      </header>

      <div className="flex-1 relative bg-slate-800 m-4 rounded-2xl overflow-hidden flex items-center justify-center">
        <div className="text-center text-slate-500 p-8">
          <p className="text-4xl mb-3">🗺️</p>
          <p className="font-semibold mb-1">Mapbox GL map renders here</p>
          <p className="text-sm">Add VITE_MAPBOX_TOKEN to .env to enable the interactive heatmap.</p>
          <p className="text-xs mt-3 text-slate-600">{heatmap.length} cells loaded</p>
        </div>
      </div>

      <div className="p-4 flex gap-4 justify-center">
        {Object.entries(RISK_COLORS).map(([level, color]) => (
          <div key={level} className="flex items-center gap-1 text-xs">
            <div className="w-3 h-3 rounded-full" style={{ background: color }} />
            <span className="text-slate-400 capitalize">{level}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
