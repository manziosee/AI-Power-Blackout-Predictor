import { useEffect, useRef } from "react";
import mapboxgl from "mapbox-gl";

interface OutagePoint {
  id: string;
  lat: number;
  lng: number;
  verified: boolean;
  reported_at: string;
}

interface Props {
  map: mapboxgl.Map;
  outages: OutagePoint[];
}

export default function OutageMarkers({ map, outages }: Props) {
  const markersRef = useRef<mapboxgl.Marker[]>([]);

  useEffect(() => {
    // Clear existing markers
    markersRef.current.forEach((m) => m.remove());
    markersRef.current = [];

    outages.forEach((outage) => {
      if (!outage.lat || !outage.lng) return;

      const el = document.createElement("div");
      el.className = "outage-marker";
      el.style.cssText = `
        width: 14px;
        height: 14px;
        background: ${outage.verified ? "#ef4444" : "#f59e0b"};
        border: 2px solid white;
        border-radius: 50%;
        cursor: pointer;
        box-shadow: 0 0 6px rgba(0,0,0,0.5);
      `;

      const popup = new mapboxgl.Popup({ offset: 12, closeButton: false })
        .setHTML(`
          <div style="color:#1e293b;font-size:12px;padding:4px">
            <strong>${outage.verified ? "✅ Confirmed" : "⚠️ Reported"} outage</strong><br/>
            ${new Date(outage.reported_at).toLocaleString()}
          </div>
        `);

      const marker = new mapboxgl.Marker(el)
        .setLngLat([outage.lng, outage.lat])
        .setPopup(popup)
        .addTo(map);

      markersRef.current.push(marker);
    });

    return () => {
      markersRef.current.forEach((m) => m.remove());
      markersRef.current = [];
    };
  }, [map, outages]);

  return null;
}
