import React from 'react';
import { View, Text, StyleSheet, SafeAreaView, ScrollView } from 'react-native';

export function ProfileScreen() {
  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.content}>
        <View style={styles.header}>
          <Text style={styles.title}>Settings</Text>
        </View>

        <View style={styles.brandSection}>
          <View style={styles.brandIcon}>
            <Text style={styles.brandEmoji}>🚌</Text>
          </View>
          <Text style={styles.brandName}>Karwan-e-Khizr</Text>
          <Text style={styles.brandUrdu}>کاروانِ خِضر</Text>
          <Text style={styles.version}>v0.1.0 — Frontend Prototype</Text>
        </View>

        <Text style={styles.sectionTitle}>PREFERENCES</Text>
        <View style={styles.settingRow}>
          <Text style={styles.settingLabel}>Language</Text>
          <Text style={styles.settingValue}>English</Text>
        </View>
        <View style={styles.settingRow}>
          <Text style={styles.settingLabel}>Theme</Text>
          <Text style={styles.settingValue}>System</Text>
        </View>
        <View style={styles.settingRow}>
          <Text style={styles.settingLabel}>Notifications</Text>
          <Text style={styles.settingValue}>Off</Text>
        </View>

        <Text style={[styles.sectionTitle, { marginTop: 24 }]}>ABOUT</Text>
        <View style={styles.settingRow}>
          <Text style={styles.settingLabel}>About Karwan-e-Khizr</Text>
          <Text style={styles.settingValue}>Islamabad–Rawalpindi Transit</Text>
        </View>

        <View style={styles.disclaimer}>
          <Text style={styles.disclaimerText}>
            This is a demo prototype. All transit data shown is simulated for demonstration purposes only.
          </Text>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#FAFAF8' },
  content: { padding: 20 },
  header: { borderBottomWidth: 1, borderBottomColor: '#ECECEA', paddingBottom: 12, marginBottom: 16 },
  title: { fontSize: 22, fontWeight: '600', color: '#1A1A1A' },
  brandSection: { alignItems: 'center', paddingVertical: 24, gap: 4 },
  brandIcon: {
    width: 64, height: 64, borderRadius: 20,
    backgroundColor: '#E8F5EC', justifyContent: 'center', alignItems: 'center',
    marginBottom: 8,
  },
  brandEmoji: { fontSize: 28 },
  brandName: { fontSize: 20, fontWeight: '700', color: '#1A1A1A' },
  brandUrdu: { fontSize: 16, color: '#5A5A5A' },
  version: { fontSize: 12, color: '#9A9A9A', marginTop: 4 },
  sectionTitle: {
    fontSize: 11, fontWeight: '600', color: '#9A9A9A', letterSpacing: 0.5,
    marginBottom: 8,
  },
  settingRow: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    padding: 14, backgroundColor: '#FFFFFF', borderRadius: 14,
    borderWidth: 1, borderColor: '#ECECEA', marginBottom: 6,
  },
  settingLabel: { fontSize: 14, fontWeight: '500', color: '#1A1A1A' },
  settingValue: { fontSize: 12, color: '#9A9A9A' },
  disclaimer: {
    marginTop: 24, padding: 16, backgroundColor: '#E8F5EC',
    borderRadius: 14,
  },
  disclaimerText: { fontSize: 12, color: '#5A5A5A', textAlign: 'center', lineHeight: 18 },
});
