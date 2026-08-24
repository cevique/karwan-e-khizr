import { useApp } from '../App';
import { MapView } from '../components/map/MapView';
import { ArrowLeft, Footprints, Bus, TrainFront, ArrowRightLeft, Navigation, Clock, MapPin } from 'lucide-react';
import type { JourneySegment, WalkSegment, TransitSegment, TransferSegment } from '@shared/types';

export function JourneyDetailScreen() {
  const { state, goBack } = useApp();
  const journey = state.selectedJourney;

  if (!journey) {
    return (
      <div style={styles.container}>
        <div style={styles.emptyState}>
          <p>No journey selected</p>
          <button style={styles.backLink} onClick={goBack}>Go back</button>
        </div>
      </div>
    );
  }

  const segIcon = (seg: JourneySegment) => {
    if (seg.type === 'walk') return <Footprints size={16} />;
    if (seg.type === 'transfer') return <ArrowRightLeft size={16} />;
    if (seg.type === 'metro') return <TrainFront size={16} />;
    return <Bus size={16} />;
  };

  return (
    <div style={styles.container}>
      <div style={styles.mapArea}>
        <MapView />
      </div>
      <div style={styles.sidePanel}>
        <div style={styles.header}>
          <button style={styles.backBtn} onClick={goBack}>
            <ArrowLeft size={20} />
          </button>
          <div style={styles.headerInfo}>
            <h2 style={styles.headerTitle}>Journey Details</h2>
            <span className="tabular-nums" style={styles.headerDuration}>{journey.totalDuration} min</span>
          </div>
        </div>

        {journey.tag && (
          <div style={styles.tagRow}>
            <span style={styles.journeyTag}>{journey.tag}</span>
            <span style={styles.fareTag}>{journey.fareLabel}</span>
          </div>
        )}

        <div style={styles.timeline}>
          {journey.segments.map((seg, i) => {
            const isFirst = i === 0;
            const isLast = i === journey.segments.length - 1;

            if (seg.type === 'walk') {
              const ws = seg as WalkSegment;
              return (
                <div key={i} style={styles.timelineItem}>
                  <div style={styles.timelineIcon}>
                    <div style={styles.walkDot} />
                    {!isLast && <div style={styles.walkLine} />}
                  </div>
                  <div style={styles.timelineContent}>
                    <div style={styles.segmentHeader}>
                      <Footprints size={14} color="var(--color-text-muted)" />
                      <span style={styles.walkLabel}>Walk {ws.duration} min</span>
                      <span style={styles.distanceLabel}>{ws.distance} m</span>
                    </div>
                    {!isFirst && (
                      <span style={styles.locationName}>{ws.from.name}</span>
                    )}
                  </div>
                </div>
              );
            }

            if (seg.type === 'transfer') {
              const ts = seg as TransferSegment;
              return (
                <div key={i} style={styles.timelineItem}>
                  <div style={styles.timelineIcon}>
                    <div style={styles.transferDot} />
                    {!isLast && <div style={styles.transferLine} />}
                  </div>
                  <div style={styles.timelineContent}>
                    <div style={styles.segmentHeader}>
                      <ArrowRightLeft size={14} color="var(--color-warning)" />
                      <span style={styles.transferLabel}>Transfer {ts.duration} min</span>
                    </div>
                    <span style={styles.transferDetail}>{ts.fromStopName}</span>
                  </div>
                </div>
              );
            }

            // Transit segment (bus or metro)
            const ts = seg as TransitSegment;
            return (
              <div key={i} style={styles.timelineItem}>
                <div style={styles.timelineIcon}>
                  <div style={{ ...styles.transitDot, background: ts.routeColor }} />
                  {!isLast && <div style={{ ...styles.transitLine, borderColor: ts.routeColor }} />}
                </div>
                <div style={styles.timelineContent}>
                  <div style={styles.segmentHeader}>
                    <div style={{ ...styles.routeBadge, background: ts.routeColor }}>
                      {ts.routeShortName}
                    </div>
                    <span style={styles.transitDirection}>{ts.direction}</span>
                  </div>
                  <div style={styles.transitInfo}>
                    <span className="tabular-nums" style={styles.transitDuration}>
                      {ts.stops} stops · {ts.duration} min
                    </span>
                  </div>
                  <div style={styles.transitStops}>
                    <div style={styles.stopPoint}>
                      <MapPin size={12} color="var(--color-text-muted)" />
                      <span style={styles.stopName}>{ts.fromStop.name}</span>
                    </div>
                    <div style={styles.stopPoint}>
                      <MapPin size={12} color="var(--color-accent-primary)" />
                      <span style={styles.stopName}>{ts.toStop.name}</span>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        <div style={styles.actions}>
          <button style={styles.trackBtn}>
            <Navigation size={16} />
            <span>Live tracking</span>
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
    display: 'flex', alignItems: 'center', gap: 12, padding: '16px 20px',
    borderBottom: '1px solid var(--color-hairline)',
  },
  backBtn: {
    width: 36, height: 36, borderRadius: 'var(--radius-sm)', border: 'none',
    background: 'transparent', color: 'var(--color-text-primary)', cursor: 'pointer',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
  },
  headerInfo: { flex: 1 },
  headerTitle: { fontSize: 15, fontWeight: 600 },
  headerDuration: { fontSize: 22, fontWeight: 700, color: 'var(--color-accent-primary)' },
  tagRow: {
    display: 'flex', gap: 8, padding: '12px 20px', alignItems: 'center',
  },
  journeyTag: {
    fontSize: 11, fontWeight: 600, color: 'var(--color-accent-primary)',
    padding: '4px 10px', background: 'var(--color-accent-primary-muted)',
    borderRadius: 'var(--radius-full)', textTransform: 'capitalize' as const,
  },
  fareTag: {
    fontSize: 13, fontWeight: 600, color: 'var(--color-text-secondary)',
  },
  timeline: { padding: '8px 20px 20px', flex: 1 },
  timelineItem: { display: 'flex', gap: 12 },
  timelineIcon: {
    display: 'flex', flexDirection: 'column', alignItems: 'center', width: 24, flexShrink: 0,
  },
  timelineContent: { flex: 1, paddingBottom: 16 },
  walkDot: {
    width: 8, height: 8, borderRadius: '50%', background: 'var(--color-text-muted)',
  },
  walkLine: {
    width: 1, flex: 1, minHeight: 20, background: 'var(--color-border)', marginTop: 4,
  },
  segmentHeader: {
    display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4,
  },
  walkLabel: { fontSize: 13, fontWeight: 600, color: 'var(--color-text-secondary)' },
  distanceLabel: { fontSize: 12, color: 'var(--color-text-muted)' },
  locationName: { fontSize: 13, color: 'var(--color-text-primary)', fontWeight: 500 },
  transferDot: {
    width: 8, height: 8, borderRadius: '50%', background: 'var(--color-warning)',
  },
  transferLine: {
    width: 1, flex: 1, minHeight: 20, background: 'var(--color-border)', marginTop: 4,
  },
  transferLabel: { fontSize: 13, fontWeight: 600, color: 'var(--color-warning)' },
  transferDetail: { fontSize: 12, color: 'var(--color-text-muted)' },
  transitDot: {
    width: 12, height: 12, borderRadius: '50%', border: '2px solid #FFF',
    boxShadow: '0 0 0 1px currentColor',
  },
  transitLine: {
    width: 0, flex: 1, minHeight: 30, borderLeft: '3px solid',
    borderLeftColor: 'inherit', marginTop: 4,
  },
  routeBadge: {
    padding: '2px 8px', borderRadius: 'var(--radius-full)', color: '#FFF',
    fontSize: 11, fontWeight: 700,
  },
  transitDirection: { fontSize: 13, color: 'var(--color-text-secondary)' },
  transitInfo: { marginTop: 4 },
  transitDuration: { fontSize: 13, fontWeight: 500, color: 'var(--color-text-primary)' },
  transitStops: { display: 'flex', flexDirection: 'column', gap: 4, marginTop: 8 },
  stopPoint: { display: 'flex', alignItems: 'center', gap: 6 },
  stopName: { fontSize: 12, color: 'var(--color-text-secondary)' },
  actions: {
    padding: '16px 20px', borderTop: '1px solid var(--color-hairline)',
  },
  trackBtn: {
    display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
    width: '100%', padding: '12px 20px',
    background: 'var(--color-accent-secondary)', color: '#FFF',
    border: 'none', borderRadius: 'var(--radius-full)',
    fontSize: 14, fontWeight: 600, cursor: 'pointer',
  },
  emptyState: {
    flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center',
    justifyContent: 'center', gap: 12, color: 'var(--color-text-muted)',
  },
  backLink: {
    border: 'none', background: 'none', color: 'var(--color-accent-primary)',
    fontSize: 14, fontWeight: 500, cursor: 'pointer',
  },
};
