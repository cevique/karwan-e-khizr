import { Heart, BookmarkPlus, Trash2, Clock, MapPin } from 'lucide-react';
import { useApp } from '../App';

export function SavedScreen() {
  const { navigate, savedJourneys, unsaveJourney, selectJourney } = useApp();

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h2 style={styles.title}>Saved Routes</h2>
      </div>
      <div style={styles.content}>
        {savedJourneys.length === 0 ? (
          <div style={styles.emptyState}>
            <div style={styles.emptyIcon}>
              <Heart size={40} strokeWidth={1.2} />
            </div>
            <h3 style={styles.emptyTitle}>No saved journeys yet</h3>
            <p style={styles.emptyText}>
              Save your favourite routes for quick access. Tap the heart icon on any journey to save it.
            </p>
            <button style={styles.exploreBtn} onClick={() => navigate('search')}>
              <BookmarkPlus size={16} />
              <span>Find a journey</span>
            </button>
          </div>
        ) : (
          <div style={styles.list}>
            {savedJourneys.map(journey => {
              const firstTransit = journey.segments.find(s => s.type === 'bus' || s.type === 'metro');
              const fromName = journey.segments[0]?.type === 'walk' ? journey.segments[0].from.name : '';
              const lastSeg = journey.segments[journey.segments.length - 1];
              const toName = lastSeg?.type === 'walk' ? lastSeg.to.name
                : lastSeg?.type === 'transfer' ? lastSeg.toStopName
                : lastSeg?.type === 'bus' || lastSeg?.type === 'metro' ? lastSeg.toStop.name
                : '';
              return (
                <div
                  key={journey.id}
                  style={styles.card}
                  onClick={() => { selectJourney(journey); navigate('journey-detail'); }}
                >
                  <div style={styles.cardTop}>
                    <span className="tabular-nums" style={styles.duration}>{journey.totalDuration} min</span>
                    {journey.tag && <span style={styles.tag}>{journey.tag}</span>}
                    <button
                      style={styles.deleteBtn}
                      onClick={(e) => { e.stopPropagation(); unsaveJourney(journey.id); }}
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                  <div style={styles.cardRoute}>
                    <MapPin size={12} color="var(--color-text-muted)" />
                    <span style={styles.routeText}>{fromName} → {toName}</span>
                  </div>
                  {firstTransit && (
                    <div style={styles.cardMeta}>
                      <span style={{ ...styles.routeBadge, background: firstTransit.type === 'bus' ? (firstTransit as any).routeColor : '#6B7280' }}>
                        {(firstTransit as any).routeShortName}
                      </span>
                      <span style={styles.fare}>{journey.fareLabel}</span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    flex: 1, display: 'flex', flexDirection: 'column', height: '100%',
    background: 'var(--color-bg)', maxWidth: 'var(--content-max-width)',
    margin: '0 auto', width: '100%',
  },
  header: {
    padding: '20px 20px 12px',
    borderBottom: '1px solid var(--color-hairline)',
  },
  title: { fontSize: 22, fontWeight: 600 },
  content: {
    flex: 1, display: 'flex', flexDirection: 'column',
    padding: 16, overflow: 'auto',
  },
  emptyState: {
    display: 'flex', flexDirection: 'column', alignItems: 'center',
    textAlign: 'center' as const, gap: 12, maxWidth: 320,
    margin: 'auto',
  },
  emptyIcon: {
    width: 80, height: 80, borderRadius: '50%',
    background: 'var(--color-surface)', border: '1px solid var(--color-hairline)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    color: 'var(--color-text-muted)', marginBottom: 8,
  },
  emptyTitle: { fontSize: 17, fontWeight: 600, color: 'var(--color-text-primary)' },
  emptyText: { fontSize: 14, color: 'var(--color-text-secondary)', lineHeight: 1.6 },
  exploreBtn: {
    display: 'flex', alignItems: 'center', gap: 8, marginTop: 12,
    padding: '12px 24px', background: 'var(--color-accent-primary)', color: '#FFF',
    border: 'none', borderRadius: 'var(--radius-full)',
    fontSize: 14, fontWeight: 600, cursor: 'pointer',
  },
  list: { display: 'flex', flexDirection: 'column', gap: 10 },
  card: {
    padding: 16, background: 'var(--color-surface)',
    borderRadius: 'var(--radius-md)', border: '1px solid var(--color-hairline)',
    cursor: 'pointer', textAlign: 'left' as const,
  },
  cardTop: { display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 },
  duration: { fontSize: 20, fontWeight: 700, color: 'var(--color-text-primary)' },
  tag: {
    fontSize: 10, fontWeight: 600, color: 'var(--color-accent-primary)',
    padding: '3px 8px', background: 'var(--color-accent-primary-muted)',
    borderRadius: 'var(--radius-full)', textTransform: 'capitalize' as const,
  },
  deleteBtn: {
    marginLeft: 'auto', background: 'none', border: 'none', cursor: 'pointer',
    color: 'var(--color-text-muted)', padding: 4,
  },
  cardRoute: { display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 },
  routeText: { fontSize: 13, color: 'var(--color-text-secondary)' },
  cardMeta: { display: 'flex', alignItems: 'center', gap: 8 },
  routeBadge: {
    padding: '2px 8px', borderRadius: 'var(--radius-full)', color: '#FFF',
    fontSize: 11, fontWeight: 700,
  },
  fare: { fontSize: 13, fontWeight: 600, color: 'var(--color-accent-primary)' },
};
