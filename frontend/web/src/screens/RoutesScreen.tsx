import { useApp } from '../App';
import { MapView } from '../components/map/MapView';
import { Route, Search } from 'lucide-react';
import { getConfig } from '@shared/services/config';

export function RoutesScreen() {
  const { navigate, transit } = useApp();
  const routes = transit.routes;

  return (
    <div style={styles.container}>
      <div style={styles.mapArea}>
        <MapView />
      </div>
      <div style={styles.sidePanel}>
        <div style={styles.header}>
          <h2 style={styles.title}>Routes</h2>
          {getConfig().useMockData && <span style={styles.demoTag}>Demo data</span>}
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
                  {route.frequency && <span style={styles.routeFreq}>{route.frequency}</span>}
                </div>
                {route.operatingHours && <span style={styles.routeHours}>{route.operatingHours}</span>}
              </div>
            ))}
          </div>
        </div>

        <div style={styles.section}>
          <button style={styles.planJourneyBtn} onClick={() => navigate('search')}>
            <Search size={16} />
            <span>Plan a journey</span>
          </button>
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
  planJourneyBtn: {
    display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
    width: '100%', padding: '14px 24px',
    background: 'var(--color-accent-primary)', color: '#FFFFFF',
    border: 'none', borderRadius: 'var(--radius-full)',
    fontSize: 15, fontWeight: 600, cursor: 'pointer',
  },
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
