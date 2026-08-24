import { Heart, BookmarkPlus } from 'lucide-react';
import { useApp } from '../App';

export function SavedScreen() {
  const { navigate } = useApp();

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h2 style={styles.title}>Saved Routes</h2>
      </div>
      <div style={styles.content}>
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
    flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center',
    padding: 32,
  },
  emptyState: {
    display: 'flex', flexDirection: 'column', alignItems: 'center',
    textAlign: 'center' as const, gap: 12, maxWidth: 320,
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
};
