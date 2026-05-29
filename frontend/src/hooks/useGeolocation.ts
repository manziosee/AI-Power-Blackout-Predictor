import { useEffect, useState } from "react";
import { lookupCell } from "../services/api";

export function useGeolocation() {
  const [coords, setCoords] = useState<{ lat: number; lng: number } | null>(null);
  const [h3Index, setH3Index] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!navigator.geolocation) {
      setError("Geolocation not supported");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const lat = pos.coords.latitude;
        const lng = pos.coords.longitude;
        setCoords({ lat, lng });
        try {
          const { data } = await lookupCell(lat, lng);
          setH3Index(data.h3_index);
        } catch {
          setError("Could not resolve neighborhood");
        }
      },
      (err) => setError(err.message)
    );
  }, []);

  return { coords, h3Index, error };
}
