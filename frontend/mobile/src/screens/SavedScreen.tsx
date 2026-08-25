import React from 'react';
import { View, Text, StyleSheet, SafeAreaView, TouchableOpacity } from 'react-native';

export function SavedScreen() {
  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Saved Routes</Text>
      </View>
      <View style={styles.content}>
        <View style={styles.emptyIcon}>
          <Text style={styles.heartIcon}>♡</Text>
        </View>
        <Text style={styles.emptyTitle}>No saved journeys yet</Text>
        <Text style={styles.emptyText}>
          Save your favourite routes for quick access. Tap the heart icon on any journey to save it.
        </Text>
        <TouchableOpacity style={styles.exploreBtn} activeOpacity={0.8}>
          <Text style={styles.exploreBtnText}>Find a journey</Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#FAFAF8' },
  header: { padding: 20, borderBottomWidth: 1, borderBottomColor: '#ECECEA' },
  title: { fontSize: 22, fontWeight: '600', color: '#1A1A1A' },
  content: {
    flex: 1, justifyContent: 'center', alignItems: 'center',
    padding: 32,
  },
  emptyIcon: {
    width: 80, height: 80, borderRadius: 40,
    backgroundColor: '#FFFFFF', borderWidth: 1, borderColor: '#ECECEA',
    justifyContent: 'center', alignItems: 'center', marginBottom: 16,
  },
  heartIcon: { fontSize: 32, color: '#9A9A9A' },
  emptyTitle: { fontSize: 17, fontWeight: '600', color: '#1A1A1A', marginBottom: 8 },
  emptyText: {
    fontSize: 14, color: '#5A5A5A', textAlign: 'center', lineHeight: 22, marginBottom: 20,
  },
  exploreBtn: {
    paddingHorizontal: 24, paddingVertical: 12,
    backgroundColor: '#1B8A4A', borderRadius: 999,
  },
  exploreBtnText: { color: '#FFFFFF', fontSize: 14, fontWeight: '600' },
});
