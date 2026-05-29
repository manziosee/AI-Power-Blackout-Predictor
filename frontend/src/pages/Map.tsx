import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import mapboxgl from "mapbox-gl";
import "mapbox-gl/dist/mapbox-gl.css";
import { useHeatmap } from "../hooks/usePredictions";
import { useUserStore } from "../store/user";
import HeatmapLayer from "../components/Map/HeatmapLayer";
import OutageMarkers from "../components/Map/OutageMarkers";
import { getCellOutages } from "../services/api";

mapboxgl.accessToken = import.meta.env.VITE_MAPBOX_TOKEN ?? "";

const RISK_LEGEND = [
  { level: "Low",      dot: "bg-risk-low" },
  { level: "Medium",   dot: "bg-risk-medium" },
  { level: "High",     dot: "bg-risk-high" },
  { level: "Critical", dot: "bg-risk-critical" },
];

export default function MapPage() {
  const mapContainer = useRef<HTMLDivElement>(null);
  const mapRef = useRef<mapboxgl.Map | null>(null);
  const [mapReady, setMapReady] = useState(false);
  const [outages, setOutages] = useState<any[]>([]);

  const user = useUserStore((s) => s.user);
  const countryCode = user?.country_code ?? "RW";
  const heatmap = useHeatmap(countryCode);

  // Default center per country
  const DEFAULT_CENTERS: Record<string, [number, number]> = {
    RW: [30.0619, -1.9441],
    KE: [36.8219, -1.2921],
    US: [-74.006, 40.7128],
    FR: [2.3522, 48.8566],
    BR: [-46.6333, -23.5505],
  };
  const center = DEFAULT_CENTERS[countryCode] ?? [0, 0];

  useEffect(() => {
    if (!mapContainer.current || mapRef.current) return;

    const map = new mapboxgl.Map({
      container: mapContainer.current,
      style: "mapbox://styles/mapbox/dark-v11",
      center,
      zoom: countryCode === "RW" ? 11 : 8,
      attributionControl: false,
    });

    map.addControl(new mapboxgl.NavigationControl(), "top-right");
    map.addControl(new mapboxgl.GeolocateControl({ positionOptions: { enableHighAccuracy: true }, trackUserLocation: true }));

    map.on("load", () => {
      setMapReady(true);
    });

    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // Load recent outage reports when clicking a cell
  useEffect(() => {
    if (!mapReady || !mapRef.current) return;
    const map = mapRef.current;

    map.on("click", "outage-circles", async (e) => {
      const features = map.queryRenderedFeatures(e.point, { layers: ["outage-circles"] });
      if (!features.length) return;
      // Fetch outages for nearby H3 — simplified: find closest cell from heatmap
      const lngLat = e.lngLat;
      const closest = heatmap.reduce((best, cell) => {
        const d = Math.abs(cell.center_lat - lngLat.lat) + Math.abs(cell.center_lng - lngLat.lng);
        return d < (Math.abs(best.center_lat - lngLat.lat) + Math.abs(best.center_lng - lngLat.lng)) ? cell : best;
      }, heatmap[0]);

      if (!closest) return;
      try {
        const { data } = await getCellOutages(closest.h3_index);
        setOutages(data.filter((r: any) => r.lat && r.lng));
      } catch {}
    });

    map.on("mouseenter", "outage-circles", () => { map.getCanvas().style.cursor = "pointer"; });
    map.on("mouseleave", "outage-circles", () => { map.getCanvas().style.cursor = ""; });
  }, [mapReady, heatmap]);

  const hasToken = !!import.meta.env.VITE_MAPBOX_TOKEN;

  return (
    <div className="h-screen bg-slate-900 flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-slate-900/90 backdrop-blur z-10">
        <div className="flex items-center gap-3">
          <Link to="/" className="text-slate-400 hover:text-white text-lg">←</Link>
          <h1 className="text-lg font-bold">Live Risk Map</h1>
        </div>
        <span className="text-xs text-slate-400">{heatmap.length} cells tracked</span>
      </div>

      {/* Map container */}
      <div className="flex-1 relative">
        {!hasToken ? (
          <div className="absolute inset-0 flex items-center justify-center bg-slate-800">
            <div className="text-center p-8 max-w-sm">
              <p className="text-4xl mb-3">🗺️</p>
              <p className="font-semibold mb-2">Mapbox token not set</p>
              <p className="text-slate-400 text-sm mb-3">
                Add <code className="bg-slate-700 px-1 rounded">VITE_MAPBOX_TOKEN</code> to your <code className="bg-slate-700 px-1 rounded">.env</code> file to enable the interactive heatmap.
              </p>
              <p className="text-slate-500 text-xs">{heatmap.length} cells loaded and ready to display</p>
            </div>
          </div>
        ) : (
          <div ref={mapContainer} className="absolute inset-0" />
        )}

        {/* Overlay: risk legend */}
        <div className="absolute bottom-6 left-4 bg-slate-900/80 backdrop-blur rounded-xl px-4 py-3 z-10">
          <p className="text-xs text-slate-400 mb-2 font-medium uppercase tracking-widest">Risk Level</p>
          <div className="flex flex-col gap-1.5">
            {RISK_LEGEND.map(({ level, dot }) => (
              <div key={level} className="flex items-center gap-2">
                <div className={`w-3 h-3 rounded-full ${dot}`} />
                <span className="text-xs text-slate-300">{level}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Render layers into map */}
        {mapReady && mapRef.current && heatmap.length > 0 && (
          <HeatmapLayer map={mapRef.current} cells={heatmap} />
        )}
        {mapReady && mapRef.current && outages.length > 0 && (
          <OutageMarkers map={mapRef.current} outages={outages} />
        )}
      </div>
    </div>
  );
}
