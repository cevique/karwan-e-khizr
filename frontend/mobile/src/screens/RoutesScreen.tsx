import React from 'react';
import { View, Text, StyleSheet, SafeAreaView, ScrollView, TouchableOpacity } from 'react-native';
import { mockRoutes } from '../../../shared/mocks/routes';
import { mockJourneys } from '../../../shared/mocks/journeys';

export function RoutesScreen() {
  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.content}>
        <View style={styles.header}>
          <Text style={styles.title}>Routes & Journeys</Text>
          <Text style={styles.demoTag}>DEMO DATA</Text>
        </View>

        <Text style={styles.sectionTitle}>TRANSIT LINES</Text>
        {mockRoutes.map(route => (
          <View key={route.id} style={styles.routeCard}>
            <View style={[styles.badge, { backgroundColor: route.color }]}>
              <Text style={styles.badgeText}>{route.shortName}</Text>
            </View>
            <View style={styles.routeInfo}>
              <Text style={styles.routeName}>{route.name}</Text>
              <Text style={styles.routeFreq}>{route.frequency}</Text>
            </View>
            <Text style={styles.routeHours}>{route.operatingHours}</Text>
          </View>
        ))}

        <Text style={[styles.sectionTitle, { marginTop: 24 }]}>SUGGESTED JOURNEYS</Text>
        {mockJourneys.map(journey => (
          <TouchableOpacity key={journey.id} style={styles.journeyCard} activeOpacity={0.7}>
            <View style={styles.journeyHeader}>
              <Text style={styles.journeyDuration}>{journey.totalDuration} min</Text>
              {journey.tag && (
                <View style={styles.journeyTagWrap}>
                  <Text style={styles.journeyTag}>{journey.tag}</Text>
                </View>
              )}
            </View>
            <Text style={styles.journeyFare}>{journey.fareLabel}</Text>
          </TouchableOpacity>
        ))}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#FAFAF8' },
  content: { padding: 20 },
  header: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    marginBottom: 20,
  },
  title: { fontSize: 22, fontWeight: '600', color: '#1A1A1A' },
  demoTag: {
    fontSize: 9, fontWeight: '600', color: '#9A9A9A',
    paddingHorizontal: 8, paddingVertical: 3,
    backgroundColor: '#F5F5F3', borderRadius: 999, overflow: 'hidden',
  },
  sectionTitle: {
    fontSize: 11, fontWeight: '600', color: '#9A9A9A', letterSpacing: 0.5,
    marginBottom: 10,
  },
  routeCard: {
    flexDirection: 'row', alignItems: 'center', gap: 12,
    padding: 14, backgroundColor: '#FFFFFF', borderRadius: 14,
    borderWidth: 1, borderColor: '#ECECEA', marginBottom: 8,
  },
  badge: {
    paddingHorizontal: 10, paddingVertical: 4, borderRadius: 999,
  },
  badgeText: { color: '#FFFFFF', fontSize: 12, fontWeight: '700' },
  routeInfo: { flex: 1 },
  routeName: { fontSize: 14, fontWeight: '600', color: '#1A1A1A' },
  routeFreq: { fontSize: 12, color: '#9A9A9A' },
  routeHours: { fontSize: 10, color: '#9A9A9A' },
  journeyCard: {
    padding: 16, backgroundColor: '#FFFFFF', borderRadius: 14,
    borderWidth: 1, borderColor: '#ECECEA', marginBottom: 8,
  },
  journeyHeader: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
  },
  journeyDuration: { fontSize: 22, fontWeight: '700', color: '#1A1A1A' },
  journeyTagWrap: {
    paddingHorizontal: 8, paddingVertical: 3,
    backgroundColor: '#E8F5EC', borderRadius: 999,
  },
  journeyTag: { fontSize: 10, fontWeight: '600', color: '#1B8A4A', textTransform: 'capitalize' },
  journeyFare: { fontSize: 14, fontWeight: '600', color: '#1B8A4A', marginTop: 8 },
});
