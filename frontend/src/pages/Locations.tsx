import { useState } from "react";
import { Link } from "react-router-dom";
import { useLocations } from "../hooks/useLocations";
import LocationCard from "../components/Locations/LocationCard";

export default function LocationsPage() {
  const { locations, loading, add, update, remove } = useLocations();
  const [showForm, setShowForm] = useState(false);
  const [h3Input, setH3Input] = useState("");
  const [labelInput, setLabelInput] = useState("");
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState("");

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    if (!h3Input.trim()) return;
    setAdding(true);
    setError("");
    try {
      await add({ h3_index: h3Input.trim(), label: labelInput.trim() || undefined, is_primary: locations.length === 0 });
      setH3Input("");
      setLabelInput("");
      setShowForm(false);
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "Failed to add location");
    }
    setAdding(false);
  }

  return (
    <div className="min-h-screen bg-slate-900 pb-8">
      <header className="flex items-center gap-3 px-4 pt-6 pb-2">
        <Link to="/" className="text-slate-400 hover:text-white text-lg">←</Link>
        <div>
          <h1 className="text-xl font-bold">My Locations</h1>
          <p className="text-xs text-slate-400">Home, office, family — each with its own alerts</p>
        </div>
      </header>

      <div className="px-4 max-w-lg mx-auto mt-4 flex flex-col gap-4">
        {/* Add button */}
        <div className="flex justify-end">
          <button
            onClick={() => setShowForm(v => !v)}
            className="text-xs bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-xl transition-colors font-semibold"
          >
            {showForm ? "Cancel" : "+ Add location"}
          </button>
        </div>

        {/* Add form */}
        {showForm && (
          <form onSubmit={handleAdd} className="bg-slate-800 rounded-2xl p-5 flex flex-col gap-3">
            <p className="text-sm font-semibold text-white">Add location</p>

            <label className="flex flex-col gap-1 text-xs text-slate-400">
              Label (optional)
              <input
                type="text"
                value={labelInput}
                onChange={e => setLabelInput(e.target.value)}
                placeholder="Home, Office, Parents…"
                className="bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 outline-none focus:border-blue-500"
              />
            </label>

            <label className="flex flex-col gap-1 text-xs text-slate-400">
              H3 cell index
              <input
                type="text"
                value={h3Input}
                onChange={e => setH3Input(e.target.value)}
                placeholder="8928308280fffff"
                required
                className="bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 outline-none focus:border-blue-500 font-mono"
              />
              <span className="text-slate-500">Tap a cell on the map to copy its H3 index</span>
            </label>

            {error && <p className="text-red-400 text-xs">{error}</p>}

            <button
              type="submit"
              disabled={adding}
              className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-semibold py-2.5 rounded-xl text-sm transition-colors"
            >
              {adding ? "Adding…" : "Add location"}
            </button>
          </form>
        )}

        {/* Location list */}
        {loading && <p className="text-slate-500 text-center py-8">Loading…</p>}

        {!loading && locations.length === 0 && (
          <div className="bg-slate-800 rounded-2xl p-10 text-center text-slate-500 flex flex-col gap-2">
            <p className="text-4xl">📍</p>
            <p className="font-semibold text-slate-400">No locations yet</p>
            <p className="text-sm">Add your home, office, or any place you want to track power for.</p>
          </div>
        )}

        {locations.map(loc => (
          <LocationCard
            key={loc.id}
            location={loc}
            onUpdate={update}
            onDelete={remove}
          />
        ))}

        {locations.length > 0 && (
          <div className="bg-slate-800/50 rounded-2xl p-4 text-xs text-slate-500 flex flex-col gap-1">
            <p className="font-semibold text-slate-400">How per-location alerts work</p>
            <p>Each location has its own risk threshold and quiet hours. When a prediction crosses the threshold for that area, you get an alert — unless it's within your quiet window. Primary location is used for your home screen risk display.</p>
          </div>
        )}
      </div>
    </div>
  );
}
