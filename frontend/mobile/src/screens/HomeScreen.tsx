import React, { useState } from 'react';
import {
  View, Text, StyleSheet, TouchableOpacity, ScrollView,
  SafeAreaView, FlatList, ActivityIndicator,
} from 'react-native';
import MapLibreGL from '@maplibre/maplibre-react-native';
import { DEFAULT_CENTER, DEFAULT_ZOOM, MAP_STYLE_LIGHT } from '../../../shared/constants';
import { useTransitData } from '../../../shared/hooks/useTransitData';

MapLibreGL.setAccessToken(null);

export function HomeScreen() {
  const [selectedBus, setSelectedBus] = useState<string | null>(null);
  const [mapReady, setMapReady] = useState(false);
  const { data: transitData, loading, error } = useTransitData();

  const buses = transitData?.vehicles ?? [];
  const stops = transitData?.stops ?? [];
  const routes = transitData?.routes ?? [];

  const busFeatures: GeoJSON.FeatureCollection = {
    type: 'FeatureCollection',
    features: buses.map(bus => ({
      type: 'Feature',
      geometry: { type: 'Point', coordinates: [bus.longitude, bus.latitude] },
      properties: { id: bus.id, routeColor: bus.routeColor, status: bus.status },
    })),
  };

  const stopFeatures: GeoJSON.FeatureCollection = {
    type: 'FeatureCollection',
    features: stops.map(stop => ({
      type: 'Feature',
      geometry: { type: 'Point', coordinates: [stop.longitude, stop.latitude] },
      properties: { id: stop.id, type: stop.type },
    })),
  };

  return (
    <SafeAreaView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <View>
          <Text style={styles.brandName}>Karwan-e-Khizr</Text>
          <Text style={styles.brandUrdu}>کاروانِ خِضر</Text>
        </View>
      </View>

      {/* Search Bar */}
      <TouchableOpacity style={styles.searchBar} activeOpacity={0.8}>
        <Text style={styles.searchIcon}>🔍</Text>
        <Text style={styles.searchPlaceholder}>Where are you going?</Text>
      </TouchableOpacity>

      {/* Map */}
      <View style={styles.mapContainer}>
        {!mapReady && (
          <View style={styles.mapLoading}>
            <ActivityIndicator size="large" color="#1B8A4A" />
            <Text style={styles.loadingText}>Loading map...</Text>
          </View>
        )}
        <MapLibreGL.MapView
          style={styles.map}
          mapStyle={MAP_STYLE_LIGHT}
          onDidFinishLoadingMap={() => setMapReady(true)}
        >
          <MapLibreGL.Camera
            defaultSettings={{
              centerCoordinate: DEFAULT_CENTER,
              zoomLevel: DEFAULT_ZOOM,
            }}
          />

          {/* Route polylines */}
          {routes.map(route => (
            <MapLibreGL.ShapeSource
              key={route.id}
              id={route.id}
              shape={{
                type: 'Feature',
                geometry: { type: 'LineString', coordinates: route.polyline },
                properties: {},
              }}
            >
              <MapLibreGL.LineLayer
                id={`${route.id}-line`}
                style={{
                  lineColor: route.color,
                  lineWidth: 3,
                  lineOpacity: 0.6,
                  lineCap: 'round',
                  lineJoin: 'round',
                }}
              />
            </MapLibreGL.ShapeSource>
          ))}

          {/* Stop markers */}
          <MapLibreGL.ShapeSource id="stops" shape={stopFeatures}>
            <MapLibreGL.CircleLayer
              id="stop-markers"
              style={{
                circleRadius: 6,
                circleColor: '#1B3A5C',
                circleStrokeWidth: 2,
                circleStrokeColor: '#FFFFFF',
              }}
            />
          </MapLibreGL.ShapeSource>

          {/* Bus markers */}
          <MapLibreGL.ShapeSource id="buses" shape={busFeatures}>
            <MapLibreGL.CircleLayer
              id="bus-markers"
              style={{
                circleRadius: 9,
                circleColor: ['get', 'routeColor'],
                circleStrokeWidth: 3,
                circleStrokeColor: '#FFFFFF',
              }}
            />
          </MapLibreGL.ShapeSource>
        </MapLibreGL.MapView>
      </View>

      {/* Nearby Buses */}
      <View style={styles.bottomSection}>
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>Nearby Buses</Text>
          <Text style={styles.demoTag}>Demo data</Text>
        </View>
        <FlatList
          data={buses}
          keyExtractor={(item) => item.id}
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.busList}
          renderItem={({ item: bus }) => (
            <TouchableOpacity
              style={[styles.busCard, selectedBus === bus.id && styles.busCardActive]}
              onPress={() => setSelectedBus(selectedBus === bus.id ? null : bus.id)}
              activeOpacity={0.7}
            >
              <View style={[styles.routeBadge, { backgroundColor: bus.routeColor }]}>
                <Text style={styles.routeBadgeText}>{bus.routeName.split(' ').pop()}</Text>
              </View>
              <Text style={styles.busRouteName}>{bus.routeName}</Text>
              <Text style={styles.busNextStop}>Next: {bus.nextStopName ?? 'Unknown'}</Text>
              <View style={styles.busMeta}>
                <Text style={styles.busStat}>{bus.eta != null ? `${bus.eta} min` : '—'}</Text>
                <Text style={styles.busStat}>{bus.speed} km/h</Text>
                {bus.status === 'scheduled' && (
                  <Text style={styles.delayTag}>Scheduled</Text>
                )}
              </View>
            </TouchableOpacity>
          )}
        />
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#FAFAF8' },
  header: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    paddingHorizontal: 20, paddingTop: 12, paddingBottom: 8,
  },
  brandName: { fontSize: 20, fontWeight: '700', color: '#1A1A1A' },
  brandUrdu: { fontSize: 13, color: '#5A5A5A' },
  searchBar: {
    flexDirection: 'row', alignItems: 'center', gap: 12,
    marginHorizontal: 16, marginBottom: 8, paddingVertical: 14, paddingHorizontal: 20,
    backgroundColor: '#FFFFFF', borderRadius: 999,
    shadowColor: '#000', shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.06, shadowRadius: 8, elevation: 3,
  },
  searchIcon: { fontSize: 16 },
  searchPlaceholder: { fontSize: 15, color: '#9A9A9A' },
  mapContainer: { flex: 1, margin: 8, borderRadius: 16, overflow: 'hidden' },
  map: { flex: 1 },
  mapLoading: {
    position: 'absolute', top: 0, left: 0, right: 0, bottom: 0,
    justifyContent: 'center', alignItems: 'center',
    backgroundColor: '#FAFAF8', zIndex: 1,
  },
  loadingText: { marginTop: 12, fontSize: 14, color: '#9A9A9A' },
  bottomSection: { maxHeight: 200, paddingTop: 8 },
  sectionHeader: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    paddingHorizontal: 20, paddingBottom: 8,
  },
  sectionTitle: { fontSize: 16, fontWeight: '600', color: '#1A1A1A' },
  demoTag: {
    fontSize: 9, fontWeight: '600', color: '#9A9A9A',
    paddingHorizontal: 8, paddingVertical: 3,
    backgroundColor: '#F5F5F3', borderRadius: 999, overflow: 'hidden',
    textTransform: 'uppercase', letterSpacing: 0.5,
  },
  busList: { paddingHorizontal: 16, gap: 10, paddingBottom: 12 },
  busCard: {
    width: 180, padding: 14, backgroundColor: '#FFFFFF',
    borderRadius: 14, borderWidth: 1, borderColor: '#ECECEA',
    gap: 6,
  },
  busCardActive: {
    borderColor: '#1B8A4A', borderWidth: 1.5,
  },
  routeBadge: {
    alignSelf: 'flex-start', paddingHorizontal: 10, paddingVertical: 3,
    borderRadius: 999,
  },
  routeBadgeText: { color: '#FFFFFF', fontSize: 11, fontWeight: '700' },
  busRouteName: { fontSize: 13, fontWeight: '600', color: '#1A1A1A' },
  busNextStop: { fontSize: 12, color: '#5A5A5A' },
  busMeta: { flexDirection: 'row', gap: 8, alignItems: 'center' },
  busStat: {
    fontSize: 11, fontWeight: '500', color: '#5A5A5A',
    paddingHorizontal: 6, paddingVertical: 2,
    backgroundColor: '#F5F5F3', borderRadius: 999, overflow: 'hidden',
  },
  delayTag: {
    fontSize: 10, fontWeight: '600', color: '#D4880F',
    paddingHorizontal: 6, paddingVertical: 2,
    backgroundColor: '#FEF3CD', borderRadius: 999, overflow: 'hidden',
  },
});
