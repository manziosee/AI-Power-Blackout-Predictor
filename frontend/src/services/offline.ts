import Dexie, { type Table } from "dexie";

interface PendingReport {
  id?: number;
  h3_index?: string;
  lat?: number;
  lng?: number;
  source: string;
  created_at: number;
  synced: boolean;
}

interface CachedPrediction {
  h3_index: string;
  data: object;
  cached_at: number;
}

class OfflineDB extends Dexie {
  pendingReports!: Table<PendingReport>;
  cachedPredictions!: Table<CachedPrediction>;

  constructor() {
    super("blackout_predictor");
    this.version(1).stores({
      pendingReports: "++id, synced",
      cachedPredictions: "h3_index",
    });
  }
}

export const db = new OfflineDB();

export async function queueOutageReport(data: Omit<PendingReport, "id" | "created_at" | "synced">) {
  await db.pendingReports.add({ ...data, created_at: Date.now(), synced: false });
}

export async function getPendingReports(): Promise<PendingReport[]> {
  return db.pendingReports.where("synced").equals(0).toArray();
}

export async function markReportSynced(id: number) {
  await db.pendingReports.update(id, { synced: true });
}

export async function cachePrediction(h3_index: string, data: object) {
  await db.cachedPredictions.put({ h3_index, data, cached_at: Date.now() });
}

export async function getCachedPrediction(h3_index: string): Promise<object | null> {
  const entry = await db.cachedPredictions.get(h3_index);
  if (!entry) return null;
  const age = (Date.now() - entry.cached_at) / 1000 / 60;
  if (age > 60) return null;   // stale after 1 hour
  return entry.data;
}
