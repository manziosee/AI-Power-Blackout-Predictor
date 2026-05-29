import { useEffect, useRef } from "react";
import mapboxgl from "mapbox-gl";
import type { HeatmapCell } from "../../store/predictions";

const RISK_COLORS: Record<string, string> = {
  low: "#22c55e",
  medium: "#f59e0b",
  high: "#ef4444",
  critical: "#7c3aed",
};

interface Props {
  map: mapboxgl.Map;
  cells: HeatmapCell[];
}

export default function HeatmapLayer({ map, cells }: Props) {
  const sourceAdded = useRef(false);

  useEffect(() => {
    if (!map || cells.length === 0) return;

    const geojson: GeoJSON.FeatureCollection = {
      type: "FeatureCollection",
      features: cells.map((cell) => ({
        type: "Feature",
        geometry: { type: "Point", coordinates: [cell.center_lng, cell.center_lat] },
        properties: {
          probability: cell.probability,
          risk_level: cell.risk_level,
          color: RISK_COLORS[cell.risk_level] ?? RISK_COLORS.low,
        },
      })),
    };

    if (!sourceAdded.current) {
      map.addSource("outage-heatmap", { type: "geojson", data: geojson });

      // Circle layer — colored dots per H3 cell center
      map.addLayer({
        id: "outage-circles",
        type: "circle",
        source: "outage-heatmap",
        paint: {
          "circle-radius": ["interpolate", ["linear"], ["zoom"], 5, 6, 10, 18, 14, 40],
          "circle-color": ["get", "color"],
          "circle-opacity": [
            "interpolate", ["linear"], ["get", "probability"],
            0, 0.15,
            0.4, 0.45,
            1, 0.80,
          ],
          "circle-blur": 0.4,
        },
      });

      sourceAdded.current = true;
    } else {
      (map.getSource("outage-heatmap") as mapboxgl.GeoJSONSource).setData(geojson);
    }
  }, [map, cells]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (map.getLayer("outage-circles")) map.removeLayer("outage-circles");
      if (map.getSource("outage-heatmap")) map.removeSource("outage-heatmap");
      sourceAdded.current = false;
    };
  }, [map]);

  return null;
}
