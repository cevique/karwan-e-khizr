import { useApp } from '../App';
import { MapView } from '../components/map/MapView';
import { mockJourneys } from '@shared/index';
import { Route, Clock, ArrowRight } from 'lucide-react';

export function RoutesScreen() {
  const { selectJourney, transit } = useApp();
  const routes = transit.routes;

  return (
    <div style={styles.container}>
      <div style={styles.mapArea}>
        <MapView />
      </div>
      <div style={styles.sidePanel}>
        <div style={styles.header}>
          <h2 style={styles.title}>Routes & Journeys</h2>
          <span style={styles.demoTag}>Demo data</span>
        </div>

        <div style={styles.section}>
          <h3 style={styles.sectionTitle}>Transit Lines</h3>
          <div style={styles.routeList}>
            {routes.map(route => (
              <div key={route.id} style={styles.routeItem}>
                <div style={{ ...styles.routeBadge, background: route.color }}>
                  {route.shortName}
                </div>
                <div style={styles.routeInfo}>
                  <span style={styles.routeName}>{route.name}</span>
                  <span style={styles.routeFreq}>{route.frequency}</span>
                </div>
                <span style={styles.routeHours}>{route.operatingHours}</span>
              </div>
            ))}
          </div>
        </div>

        <div style={styles.section}>
          <h3 style={styles.sectionTitle}>Suggested Journeys</h3>
          <div style={styles.journeyList}>
            {mockJourneys.map((journey, i) => (
              <button
                key={journey.id}
                style={{
                  ...styles.journeyCard,
                  animationDelay: `${i * 80}ms`,
                }}
                onClick={() => selectJourney(journey)}
              >
                <div style={styles.journeyTop}>
                  <span className="tabular-nums" style={styles.journeyDuration}>{journey.totalDuration} min</span>
                  {journey.tag && (
                    <span style={styles.journeyTag}>{journey.tag}</span>
                  )}
                </div>
                <div style={styles.journeyPath}>
                  {journey.segments.map((seg, si) => (
                    <span key={si} style={styles.pathSegment}>
                      {seg.type === 'walk' ? '🚶' : seg.type === 'transfer' ? '↔' : '🚌'}
                      {si < journey.segments.length - 1 && <ArrowRight size={12} style={styles.pathArrow} />}
                    </span>
                  ))}
                </div>
                <span style={styles.journeyFare}>{journey.fareLabel}</span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: { display: 'flex', flex: 1, height: '100%', overflow: 'hidden' },
  mapArea: { flex: 1, position: 'relative', minWidth: 0 },
  sidePanel: {
    width: 380, height: '100%', borderLeft: '1px solid var(--color-hairline)',
    background: 'var(--color-bg)', display: 'flex', flexDirection: 'column', overflow: 'auto', flexShrink: 0,
  },
  header: {
    display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '20px 20px 12px',
  },
  title: { fontSize: 17, fontWeight: 600 },
  demoTag: {
    fontSize: 10, fontWeight: 500, color: 'var(--color-text-muted)', padding: '3px 8px',
    background: 'var(--color-surface-hover)', borderRadius: 'var(--radius-full)', textTransform: 'uppercase' as const,
  },
  section: { padding: '0 16px 16px' },
  sectionTitle: {
    fontSize: 12, fontWeight: 600, color: 'var(--color-text-muted)', textTransform: 'uppercase' as const,
    letterSpacing: '0.5px', padding: '12px 4px 8px',
  },
  routeList: { display: 'flex', flexDirection: 'column', gap: 8 },
  routeItem: {
    display: 'flex', alignItems: 'center', gap: 12, padding: 14,
    background: 'var(--color-surface)', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-hairline)',
  },
  routeBadge: {
    padding: '4px 10px', borderRadius: 'var(--radius-full)', color: '#FFF',
    fontSize: 12, fontWeight: 700, letterSpacing: '0.3px',
  },
  routeInfo: { flex: 1, display: 'flex', flexDirection: 'column', gap: 2 },
  routeName: { fontSize: 14, fontWeight: 600, color: 'var(--color-text-primary)' },
  routeFreq: { fontSize: 12, color: 'var(--color-text-muted)' },
  routeHours: { fontSize: 11, color: 'var(--color-text-muted)', flexShrink: 0 },
  journeyList: { display: 'flex', flexDirection: 'column', gap: 8 },
  journeyCard: {
    display: 'flex', flexDirection: 'column', gap: 8, padding: 16,
    background: 'var(--color-surface)', borderRadius: 'var(--radius-md)',
    border: '1px solid var(--color-hairline)', cursor: 'pointer', textAlign: 'left' as const,
    transition: 'all var(--duration-fast) var(--ease-smooth)',
    animation: 'slideUp var(--duration-normal) var(--ease-spring) both',
  },
  journeyTop: { display: 'flex', justifyContent: 'space-between', alignItems: 'center' },
  journeyDuration: { fontSize: 20, fontWeight: 700, color: 'var(--color-text-primary)' },
  journeyTag: {
    fontSize: 10, fontWeight: 600, color: 'var(--color-accent-primary)',
    padding: '3px 8px', background: 'var(--color-accent-primary-muted)',
    borderRadius: 'var(--radius-full)', textTransform: 'capitalize' as const,
  },
  journeyPath: { display: 'flex', alignItems: 'center', gap: 4 },
  pathSegment: { display: 'flex', alignItems: 'center', gap: 4, fontSize: 14 },
  pathArrow: { color: 'var(--color-text-muted)', marginLeft: 4 },
  journeyFare: { fontSize: 14, fontWeight: 600, color: 'var(--color-accent-primary)' },
};
