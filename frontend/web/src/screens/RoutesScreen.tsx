import { useApp } from '../App';
import { MapView } from '../components/map/MapView';
import { useMediaQuery } from '../hooks/useMediaQuery';
import { ArrowLeft, Route, Search, Clock, Gauge } from 'lucide-react';
import { getConfig } from '@shared/services/config';

export function RoutesScreen() {
  const { navigate, transit, state, selectedBus, selectRoute } = useApp();
  const routes = transit.routes;
  const isDesktop = useMediaQuery('(min-width: 768px)');
  const selectedRoute = state.selectedRoute;
  const routeStops = state.routeStops;

  return (
    <div style={{ ...styles.container, flexDirection: isDesktop ? 'row' : 'column' }}>
      <div style={styles.mapArea}>
        <MapView />
        {selectedBus && (
          <div style={styles.floatingCard}>
            <div style={styles.cardHeader}>
              <div style={{ ...styles.routeBadge, background: selectedBus.routeColor }}>
                {selectedBus.routeName.split(' ').pop()}
              </div>
              <span style={styles.cardTitle}>{selectedBus.routeName}</span>
            </div>
            <div style={styles.cardDetail}>
              <span style={styles.cardLabel}>Next stop:</span>
              <span style={styles.cardValue}>{selectedBus.nextStopName ?? 'Unknown'}</span>
            </div>
            <div style={styles.cardMeta}>
              <span className="tabular-nums" style={styles.cardChip}>
                <Clock size={12} /> {selectedBus.eta != null ? `${selectedBus.eta} min` : '—'}
              </span>
              <span className="tabular-nums" style={styles.cardChip}>
                <Gauge size={12} /> {selectedBus.speed} km/h
              </span>
            </div>
          </div>
        )}
        {state.selectedStop && (
          <div style={styles.floatingCard}>
            <div style={styles.cardHeader}>
              <div style={styles.stopDot} />
              <span style={styles.cardTitle}>{state.selectedStop.name}</span>
            </div>
          </div>
        )}
      </div>
      <div style={{
        ...styles.sidePanel,
        ...(isDesktop
          ? { width: 380, height: '100%', borderLeft: '1px solid var(--color-hairline)', flexShrink: 0 }
          : { position: 'fixed', bottom: 60, left: 0, right: 0, width: '100%', height: '50vh', borderTop: '1px solid var(--color-hairline)', borderRadius: '16px 16px 0 0', zIndex: 20 }
        ),
      }}>
        {selectedRoute ? (
          <>
            <div style={styles.header}>
              <button style={styles.backBtn} onClick={() => selectRoute(null)}>
                <ArrowLeft size={20} />
              </button>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <div style={{ ...styles.routeBadge, background: selectedRoute.color }}>
                  {selectedRoute.shortName}
                </div>
                <span style={styles.title}>{selectedRoute.name}</span>
              </div>
            </div>
            <div style={styles.section}>
              <h3 style={styles.sectionTitle}>Stops ({routeStops?.stops.length ?? '…'})</h3>
              <div style={styles.routeList}>
                {routeStops?.stops.map((stop, i) => (
                  <div key={stop.stopId} style={styles.routeItem}>
                    <div style={styles.stopNumber}>{i + 1}</div>
                    <div style={styles.routeInfo}>
                      <span style={styles.routeName}>{stop.stopName}</span>
                    </div>
                  </div>
                ))}
                {!routeStops && (
                  <div style={{ padding: 20, textAlign: 'center', color: 'var(--color-text-muted)' }}>
                    Loading stops…
                  </div>
                )}
              </div>
            </div>
          </>
        ) : (
          <>
            <div style={styles.header}>
              <h2 style={styles.title}>Routes</h2>
              {getConfig().useMockData && <span style={styles.demoTag}>Demo data</span>}
            </div>
            <div style={styles.section}>
              <h3 style={styles.sectionTitle}>Transit Lines</h3>
              <div style={styles.routeList}>
                {routes.map(route => (
                  <div key={route.id} style={{ ...styles.routeItem, cursor: 'pointer' }} onClick={() => selectRoute(route)}>
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
          </>
        )}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: { display: 'flex', flex: 1, height: '100%', overflow: 'hidden' },
  mapArea: { flex: 1, position: 'relative', minWidth: 0 },
  sidePanel: {
    background: 'var(--color-bg)', display: 'flex', flexDirection: 'column', overflow: 'auto',
  },
  header: {
    display: 'flex', alignItems: 'center', gap: 8, padding: '20px 20px 12px',
  },
  backBtn: {
    width: 36, height: 36, borderRadius: 'var(--radius-sm)', border: 'none',
    background: 'transparent', color: 'var(--color-text-primary)', cursor: 'pointer',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
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
  stopNumber: {
    width: 24, height: 24, borderRadius: '50%', background: 'var(--color-surface-hover)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    fontSize: 11, fontWeight: 600, color: 'var(--color-text-muted)', flexShrink: 0,
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
  floatingCard: {
    position: 'absolute', bottom: 16, left: 16, right: 16,
    padding: 14, background: 'var(--color-surface)',
    borderRadius: 'var(--radius-md)', border: '1px solid var(--color-hairline)',
    boxShadow: '0 4px 12px rgba(0,0,0,0.1)', zIndex: 10,
  },
  cardHeader: { display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 },
  cardTitle: { fontSize: 14, fontWeight: 600, color: 'var(--color-text-primary)' },
  cardDetail: { display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 },
  cardLabel: { fontSize: 12, color: 'var(--color-text-muted)' },
  cardValue: { fontSize: 13, fontWeight: 500, color: 'var(--color-text-secondary)' },
  cardMeta: { display: 'flex', gap: 8 },
  cardChip: {
    display: 'flex', alignItems: 'center', gap: 4,
    fontSize: 12, color: 'var(--color-text-secondary)',
  },
  stopDot: {
    width: 10, height: 10, borderRadius: '50%',
    background: 'var(--color-accent-primary)', flexShrink: 0,
  },
};
