import { useEffect } from "react";
import { getCellPredictions, getHeatmap } from "../services/api";
import { cachePrediction, getCachedPrediction } from "../services/offline";
import { usePredictionsStore } from "../store/predictions";

export function usePredictions(h3_index: string) {
  const { predictions, setPredictions, setLoading } = usePredictionsStore();

  useEffect(() => {
    if (!h3_index) return;

    async function load() {
      setLoading(true);
      const cached = await getCachedPrediction(h3_index);
      if (cached) {
        setPredictions(h3_index, cached as any);
        setLoading(false);
        return;
      }
      try {
        const { data } = await getCellPredictions(h3_index);
        setPredictions(h3_index, data);
        await cachePrediction(h3_index, data);
      } catch {
        // network offline — cached data already shown if available
      } finally {
        setLoading(false);
      }
    }

    load();
  }, [h3_index]);

  return predictions[h3_index] ?? [];
}

export function useHeatmap(country_code: string) {
  const { heatmap, setHeatmap } = usePredictionsStore();

  useEffect(() => {
    if (!country_code) return;
    getHeatmap(country_code)
      .then(({ data }) => setHeatmap(data))
      .catch(() => {});
  }, [country_code]);

  return heatmap;
}
