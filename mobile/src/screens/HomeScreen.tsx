import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  FlatList,
  RefreshControl,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { getHealth, getHeatmap } from "../services/api";

interface CellSummary {
  h3_index: string;
  probability: number;
  risk_level: string;
}

const RISK_COLORS: Record<string, string> = {
  low: "#22c55e",
  medium: "#f59e0b",
  high: "#ef4444",
  critical: "#7c3aed",
};

export default function HomeScreen({ navigation }: { navigation: any }) {
  const [cells, setCells] = useState<CellSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [apiStatus, setApiStatus] = useState<"ok" | "error">("ok");

  const load = useCallback(async () => {
    try {
      const [heatmap, health] = await Promise.all([getHeatmap(), getHealth()]);
      setApiStatus(health.status === "ok" ? "ok" : "error");
      const features = heatmap?.features ?? [];
      const sorted = features
        .map((f: any) => ({
          h3_index: f.properties.h3_index,
          probability: f.properties.probability,
          risk_level: f.properties.risk_level,
        }))
        .sort((a: CellSummary, b: CellSummary) => b.probability - a.probability);
      setCells(sorted.slice(0, 50));
    } catch {
      setApiStatus("error");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#6366f1" />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Blackout Predictor</Text>
        <View style={[styles.dot, { backgroundColor: apiStatus === "ok" ? "#22c55e" : "#ef4444" }]} />
      </View>
      <FlatList
        data={cells}
        keyExtractor={(item) => item.h3_index}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load(); }} />}
        renderItem={({ item }) => (
          <TouchableOpacity
            style={styles.card}
            onPress={() => navigation.navigate("Map", { h3_index: item.h3_index })}
          >
            <View style={[styles.riskBadge, { backgroundColor: RISK_COLORS[item.risk_level] ?? "#94a3b8" }]}>
              <Text style={styles.riskText}>{item.risk_level.toUpperCase()}</Text>
            </View>
            <View style={styles.cardBody}>
              <Text style={styles.h3Label}>{item.h3_index}</Text>
              <Text style={styles.prob}>{Math.round(item.probability * 100)}% risk</Text>
            </View>
          </TouchableOpacity>
        )}
        ListEmptyComponent={<Text style={styles.empty}>No predictions available</Text>}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#0f172a" },
  center: { flex: 1, justifyContent: "center", alignItems: "center", backgroundColor: "#0f172a" },
  header: { flexDirection: "row", alignItems: "center", padding: 16, paddingTop: 48 },
  title: { flex: 1, color: "#f1f5f9", fontSize: 22, fontWeight: "700" },
  dot: { width: 10, height: 10, borderRadius: 5 },
  card: { flexDirection: "row", alignItems: "center", margin: 8, backgroundColor: "#1e293b", borderRadius: 12, overflow: "hidden" },
  riskBadge: { width: 64, height: 64, justifyContent: "center", alignItems: "center" },
  riskText: { color: "#fff", fontSize: 10, fontWeight: "700" },
  cardBody: { flex: 1, padding: 12 },
  h3Label: { color: "#94a3b8", fontSize: 12, fontFamily: "monospace" },
  prob: { color: "#f1f5f9", fontSize: 18, fontWeight: "600", marginTop: 4 },
  empty: { textAlign: "center", color: "#64748b", marginTop: 48, fontSize: 16 },
});
