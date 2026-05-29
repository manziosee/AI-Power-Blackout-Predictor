import { useEffect, useState } from "react";
import { getPendingReports, markReportSynced } from "../services/offline";
import { reportOutage } from "../services/api";

export function useOfflineSync() {
  const [syncing, setSyncing] = useState(false);

  useEffect(() => {
    const handler = async () => {
      if (!navigator.onLine) return;
      const pending = await getPendingReports();
      if (!pending.length) return;

      setSyncing(true);
      for (const report of pending) {
        try {
          await reportOutage({ h3_index: report.h3_index, lat: report.lat, lng: report.lng });
          if (report.id) await markReportSynced(report.id);
        } catch {
          // will retry next time online
        }
      }
      setSyncing(false);
    };

    window.addEventListener("online", handler);
    handler(); // try immediately on mount
    return () => window.removeEventListener("online", handler);
  }, []);

  return { syncing };
}
