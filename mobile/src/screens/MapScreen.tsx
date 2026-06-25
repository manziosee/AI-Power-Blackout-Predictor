import React, { useEffect, useRef, useState } from "react";
import { ActivityIndicator, StyleSheet, Text, View } from "react-native";
import MapView, { Circle, Marker } from "react-native-maps";
import { getHeatmap } from "../services/api";

interface CellFeature {
  h3_index: string;
  lat: number;
  lng: number;
  probability: number;
  risk_level: string;
}

const RISK_COLORS: Record<string, string> = {
  low: "#22c55e",
  medium: "#f59e0b",
  high: "#ef4444",
  critical: "#7c3aed",
};

export default function MapScreen({ route }: { route: any }) {
  const focusH3: string | undefined = route?.params?.h3_index;
  const [features, setFeatures] = useState<CellFeature[]>([]);
  const [loading, setLoading] = useState(true);
  const mapRef = useRef<MapView>(null);

  useEffect(() => {
    getHeatmap()
      .then((data: any) => {
        const cells: CellFeature[] = (data?.features ?? []).map((f: any) => ({
          h3_index: f.properties.h3_index,
          lat: f.geometry.coordinates[1],
          lng: f.geometry.coordinates[0],
          probability: f.properties.probability,
          risk_level: f.properties.risk_level,
        }));
        setFeatures(cells);
        if (focusH3) {
          const target = cells.find((c) => c.h3_index === focusH3);
          if (target) {
            mapRef.current?.animateToRegion({
              latitude: target.lat,
              longitude: target.lng,
              latitudeDelta: 0.05,
              longitudeDelta: 0.05,
            });
          }
        }
      })
      .finally(() => setLoading(false));
  }, [focusH3]);

  return (
    <View style={styles.container}>
      <MapView
        ref={mapRef}
        style={styles.map}
        initialRegion={{ latitude: 0, longitude: 20, latitudeDelta: 30, longitudeDelta: 30 }}
      >
        {features.map((cell) => (
          <Circle
            key={cell.h3_index}
            center={{ latitude: cell.lat, longitude: cell.lng }}
            radius={5000}
            fillColor={`${RISK_COLORS[cell.risk_level] ?? "#94a3b8"}66`}
            strokeColor={RISK_COLORS[cell.risk_level] ?? "#94a3b8"}
            strokeWidth={1}
          />
        ))}
      </MapView>
      {loading && (
        <View style={styles.overlay}>
          <ActivityIndicator size="large" color="#6366f1" />
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  map: { flex: 1 },
  overlay: {
    ...StyleSheet.absoluteFillObject,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: "rgba(15,23,42,0.6)",
  },
});
