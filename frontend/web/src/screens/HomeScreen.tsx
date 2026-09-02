import { useApp } from '../App';
import { MapView } from '../components/map/MapView';
import { Search, Bus, Clock, Gauge, ChevronRight, LocateFixed, Layers, Loader2, AlertTriangle } from 'lucide-react';

export function HomeScreen() {
  const { navigate, state, selectBus, selectStop, transit } = useApp();
  const buses = transit.vehicles;
  const loading = transit.transitLoading;
  const error = transit.transitError;

  return (
    <div style={styles.container}>
      {/* Map area */}
      <div style={styles.mapArea}>
        <MapView />

        {/* Floating search bar */}
        <div style={styles.searchOverlay}>
          <button style={styles.searchBar} onClick={() => navigate('search')}>
            <Search size={18} color="var(--color-text-muted)" />
            <span style={styles.searchPlaceholder}>Where are you going?</span>
          </button>
        </div>

        {/* Map controls */}
        <div style={styles.mapControls}>
          <button style={styles.mapControlBtn} title="Locate me">
            <LocateFixed size={18} />
          </button>
          <button style={styles.mapControlBtn} title="Map layers">
            <Layers size={18} />
          </button>
        </div>

        {/* Selected bus/stop card overlay on map */}
        {state.selectedBus && (
          <div style={styles.floatingCard} onClick={() => {}}>
            <div style={styles.cardHeader}>
              <div style={{ ...styles.routeBadge, background: state.selectedBus.routeColor }}>
                {state.selectedBus.routeName.split(' ').pop()}
              </div>
              <span style={styles.cardTitle}>{state.selectedBus.routeName}</span>
            </div>
            <div style={styles.cardDetail}>
              <span style={styles.cardLabel}>Next stop:</span>
              <span style={styles.cardValue}>{state.selectedBus.nextStopName ?? 'Unknown'}</span>
            </div>
            <div style={styles.cardMeta}>
              <span className="tabular-nums" style={styles.cardChip}>
                <Clock size={12} /> {state.selectedBus.eta != null ? `${state.selectedBus.eta} min` : '—'}
              </span>
              <span className="tabular-nums" style={styles.cardChip}>
                <Gauge size={12} /> {state.selectedBus.speed} km/h
              </span>
              {state.selectedBus.status === 'scheduled' && (
                <span style={styles.delayBadge}>Not yet en route</span>
              )}
            </div>
          </div>
        )}

        {state.selectedStop && (
          <div style={styles.floatingCard}>
            <div style={styles.cardHeader}>
              <div style={styles.stopDot} />
              <span style={styles.cardTitle}>{state.selectedStop.name}</span>
            </div>
            {state.selectedStop.nameUrdu && (
              <span className="urdu" style={styles.urduName}>{state.selectedStop.nameUrdu}</span>
            )}
            <div style={styles.cardDetail}>
              <span style={styles.cardLabel}>Type:</span>
              <span style={styles.cardValue}>{state.selectedStop.type.replace('-', ' ')}</span>
            </div>
          </div>
        )}
      </div>

      {/* Side panel (desktop) / bottom content area (mobile handled by MobileShell) */}
      <div style={styles.sidePanel}>
        <div style={styles.panelHeader}>
          <h2 style={styles.panelTitle}>Nearby Buses</h2>
          {transit.transitError && (
            <span style={styles.errorTag}>Using offline data</span>
          )}
          {!transit.transitError && (
            <span style={styles.demoTag}>Demo data</span>
          )}
        </div>

        {loading && buses.length === 0 && (
          <div style={styles.loadingState}>
            <Loader2 size={20} style={{ animation: 'spin 1s linear infinite' }} />
            <span style={styles.loadingText}>Loading vehicles…</span>
          </div>
        )}

        {error && buses.length === 0 && (
          <div style={styles.errorState}>
            <AlertTriangle size={20} color="var(--color-warning)" />
            <span style={styles.errorText}>Could not load transit data</span>
          </div>
        )}

        {!loading && !error && buses.length === 0 && (
          <div style={styles.emptyState}>
            <Bus size={20} color="var(--color-text-muted)" />
            <span style={styles.emptyText}>No buses nearby</span>
          </div>
        )}

        <div style={styles.busList}>
          {buses.map((bus, i) => (
            <button
              key={bus.id}
              style={{
                ...styles.busCard,
                animationDelay: `${i * 60}ms`,
                ...(state.selectedBus?.id === bus.id ? styles.busCardActive : {}),
              }}
              onClick={() => {
                selectBus(state.selectedBus?.id === bus.id ? null : bus);
              }}
            >
              <div style={styles.busCardTop}>
                <div style={{ ...styles.routeBadge, background: bus.routeColor }}>
                  {bus.routeName.split(' ').pop()}
                </div>
                <div style={styles.busCardInfo}>
                  <span style={styles.busRouteName}>{bus.routeName}</span>
                  <span style={styles.busVehicle}>{bus.vehicleNumber}</span>
                </div>
                <ChevronRight size={16} color="var(--color-text-muted)" />
              </div>
              <div style={styles.busCardBottom}>
                <div style={styles.busCardMeta}>
                  <Bus size={13} color="var(--color-text-muted)" />
                  <span style={styles.busNextStop}>Next: {bus.nextStopName ?? 'Unknown'}</span>
                </div>
                <div style={styles.busCardStats}>
                  <span className="tabular-nums" style={styles.stat}>
                    <Clock size={12} /> {bus.eta != null ? `${bus.eta} min` : '—'}
                  </span>
                  <span className="tabular-nums" style={styles.stat}>
                    <Gauge size={12} /> {bus.speed} km/h
                  </span>
                  {bus.status === 'scheduled' && (
                    <span style={styles.delayTag}>Scheduled</span>
                  )}
                </div>
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flex: 1,
    height: '100%',
    overflow: 'hidden',
  },
  mapArea: {
    flex: 1,
    position: 'relative',
    minWidth: 0,
  },
  searchOverlay: {
    position: 'absolute',
    top: 16,
    left: 16,
    right: 16,
    zIndex: 10,
    maxWidth: 480,
  },
  searchBar: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    width: '100%',
    padding: '14px 20px',
    background: 'var(--color-surface)',
    borderRadius: 'var(--radius-full)',
    border: 'none',
    boxShadow: 'var(--shadow-2)',
    cursor: 'pointer',
    transition: 'box-shadow var(--duration-fast) var(--ease-smooth)',
  },
  searchPlaceholder: {
    fontSize: 15,
    color: 'var(--color-text-muted)',
    fontWeight: 400,
  },
  mapControls: {
    position: 'absolute',
    bottom: 24,
    right: 16,
    display: 'flex',
    flexDirection: 'column',
    gap: 8,
    zIndex: 10,
  },
  mapControlBtn: {
    width: 44,
    height: 44,
    borderRadius: 'var(--radius-md)',
    background: 'var(--color-surface)',
    border: 'none',
    boxShadow: 'var(--shadow-2)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    cursor: 'pointer',
    color: 'var(--color-text-secondary)',
    transition: 'all var(--duration-fast) var(--ease-smooth)',
  },
  floatingCard: {
    position: 'absolute',
    bottom: 24,
    left: 16,
    right: 80,
    maxWidth: 360,
    background: 'var(--color-surface)',
    borderRadius: 'var(--radius-lg)',
    padding: 16,
    boxShadow: 'var(--shadow-2)',
    zIndex: 10,
    animation: 'slideUp var(--duration-normal) var(--ease-spring)',
  },
  cardHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    marginBottom: 8,
  },
  cardTitle: {
    fontSize: 15,
    fontWeight: 600,
    color: 'var(--color-text-primary)',
  },
  routeBadge: {
    padding: '3px 10px',
    borderRadius: 'var(--radius-full)',
    color: '#FFFFFF',
    fontSize: 12,
    fontWeight: 700,
    letterSpacing: '0.3px',
  },
  cardDetail: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    marginBottom: 4,
  },
  cardLabel: {
    fontSize: 13,
    color: 'var(--color-text-muted)',
  },
  cardValue: {
    fontSize: 13,
    fontWeight: 500,
    color: 'var(--color-text-primary)',
  },
  cardMeta: {
    display: 'flex',
    gap: 8,
    marginTop: 8,
  },
  cardChip: {
    display: 'flex',
    alignItems: 'center',
    gap: 4,
    fontSize: 12,
    fontWeight: 500,
    color: 'var(--color-text-secondary)',
    padding: '3px 8px',
    background: 'var(--color-surface-hover)',
    borderRadius: 'var(--radius-full)',
  },
  delayBadge: {
    fontSize: 11,
    fontWeight: 600,
    color: 'var(--color-warning)',
    padding: '3px 8px',
    background: '#FEF3CD',
    borderRadius: 'var(--radius-full)',
  },
  stopDot: {
    width: 10,
    height: 10,
    borderRadius: '50%',
    background: 'var(--color-accent-secondary)',
    border: '2px solid #FFFFFF',
    boxShadow: '0 0 0 1px var(--color-accent-secondary)',
  },
  urduName: {
    fontSize: 13,
    color: 'var(--color-text-secondary)',
    marginBottom: 4,
  },
  sidePanel: {
    width: 380,
    height: '100%',
    borderLeft: '1px solid var(--color-hairline)',
    background: 'var(--color-bg)',
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
    flexShrink: 0,
  },
  panelHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '20px 20px 12px',
  },
  panelTitle: {
    fontSize: 17,
    fontWeight: 600,
    color: 'var(--color-text-primary)',
  },
  demoTag: {
    fontSize: 10,
    fontWeight: 500,
    color: 'var(--color-text-muted)',
    padding: '3px 8px',
    background: 'var(--color-surface-hover)',
    borderRadius: 'var(--radius-full)',
    letterSpacing: '0.3px',
    textTransform: 'uppercase' as const,
  },
  busList: {
    flex: 1,
    overflow: 'auto',
    padding: '0 12px 12px',
    display: 'flex',
    flexDirection: 'column',
    gap: 8,
  },
  busCard: {
    display: 'flex',
    flexDirection: 'column',
    gap: 10,
    padding: 16,
    background: 'var(--color-surface)',
    borderRadius: 'var(--radius-md)',
    border: '1px solid var(--color-hairline)',
    cursor: 'pointer',
    transition: 'all var(--duration-fast) var(--ease-smooth)',
    textAlign: 'left' as const,
    animation: 'slideUp var(--duration-normal) var(--ease-spring) both',
  },
  busCardActive: {
    borderColor: 'var(--color-accent-primary)',
    boxShadow: '0 0 0 1px var(--color-accent-primary)',
  },
  busCardTop: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
  },
  busCardInfo: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    gap: 1,
  },
  busRouteName: {
    fontSize: 14,
    fontWeight: 600,
    color: 'var(--color-text-primary)',
  },
  busVehicle: {
    fontSize: 11,
    color: 'var(--color-text-muted)',
    fontWeight: 500,
  },
  busCardBottom: {
    display: 'flex',
    flexDirection: 'column',
    gap: 6,
  },
  busCardMeta: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
  },
  busNextStop: {
    fontSize: 13,
    color: 'var(--color-text-secondary)',
  },
  busCardStats: {
    display: 'flex',
    gap: 8,
    alignItems: 'center',
  },
  stat: {
    display: 'flex',
    alignItems: 'center',
    gap: 4,
    fontSize: 12,
    fontWeight: 500,
    color: 'var(--color-text-secondary)',
  },
  delayTag: {
    fontSize: 10,
    fontWeight: 600,
    color: 'var(--color-warning)',
    padding: '2px 6px',
    background: '#FEF3CD',
    borderRadius: 'var(--radius-full)',
    marginLeft: 'auto',
  },
  errorTag: {
    fontSize: 10,
    fontWeight: 500,
    color: 'var(--color-warning)',
    padding: '3px 8px',
    background: '#FEF3CD',
    borderRadius: 'var(--radius-full)',
    letterSpacing: '0.3px',
    textTransform: 'uppercase' as const,
  },
  loadingState: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    padding: '32px 20px',
    color: 'var(--color-text-muted)',
  },
  loadingText: {
    fontSize: 13,
    fontWeight: 500,
    color: 'var(--color-text-muted)',
  },
  errorState: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    padding: '32px 20px',
  },
  errorText: {
    fontSize: 13,
    fontWeight: 500,
    color: 'var(--color-warning)',
  },
  emptyState: {
    display: 'flex',
    flexDirection: 'column' as const,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    padding: '32px 20px',
  },
  emptyText: {
    fontSize: 13,
    fontWeight: 500,
    color: 'var(--color-text-muted)',
  },
};
