import { useState } from 'react';
import { useApp } from '../App';
import { Search, ArrowLeft, MapPin, TrainFront, Building2, X, ArrowUpDown, Clock, Loader2 } from 'lucide-react';
import { mockSearchResults, mockJourneys } from '@shared/index';
import { useSearchResults } from '@shared/hooks/useTransitData';

export function SearchScreen() {
  const { state, navigate, setSearchOrigin, setSearchDestination, selectJourney } = useApp();
  const [query, setQuery] = useState('');
  const [activeField, setActiveField] = useState<'from' | 'to'>('to');
  const [showJourneys, setShowJourneys] = useState(false);

  // Use the service layer for search results
  const { data: searchResults, loading: searchLoading } = useSearchResults(query);
  // Fall back to full list when query is empty
  const filtered = query.length > 0 ? searchResults : mockSearchResults;

  const handleSelect = (name: string) => {
    if (activeField === 'from') setSearchOrigin(name);
    else setSearchDestination(name);
    setQuery('');
  };

  const handleSearch = () => {
    if (state.searchOrigin && state.searchDestination) {
      setShowJourneys(true);
    }
  };

  const handleSwap = () => {
    const tmp = state.searchOrigin;
    setSearchOrigin(state.searchDestination);
    setSearchDestination(tmp);
  };

  const iconForType = (type: string) => {
    if (type === 'stop') return <MapPin size={16} color="var(--color-accent-secondary)" />;
    if (type === 'station') return <TrainFront size={16} color="var(--color-accent-primary)" />;
    return <Building2 size={16} color="var(--color-text-muted)" />;
  };

  if (showJourneys) {
    return (
      <div style={styles.container}>
        <div style={styles.header}>
          <button style={styles.backBtn} onClick={() => setShowJourneys(false)}>
            <ArrowLeft size={20} />
          </button>
          <h2 style={styles.headerTitle}>Journey Results</h2>
        </div>
        <div style={styles.summaryBar}>
          <span style={styles.summaryText}>{state.searchOrigin} → {state.searchDestination}</span>
          <span style={styles.demoTag}>Demo</span>
        </div>
        <div style={styles.journeyList}>
          {mockJourneys.map((journey, i) => (
            <button
              key={journey.id}
              style={{
                ...styles.journeyCard,
                animationDelay: `${i * 80}ms`,
                ...(journey.tag === 'recommended' ? styles.journeyCardBest : {}),
              }}
              onClick={() => selectJourney(journey)}
            >
              <div style={styles.journeyTop}>
                <div style={styles.journeyDuration}>
                  <span className="tabular-nums" style={styles.durationNum}>{journey.totalDuration}</span>
                  <span style={styles.durationUnit}>min</span>
                </div>
                {journey.tag && (
                  <span style={{
                    ...styles.journeyTag,
                    ...(journey.tag === 'recommended' ? styles.tagRecommended :
                       journey.tag === 'fastest' ? styles.tagFastest : styles.tagWalking),
                  }}>
                    {journey.tag}
                  </span>
                )}
              </div>
              <div style={styles.journeySegments}>
                {journey.segments.map((seg, si) => (
                  <span key={si} style={styles.segmentLabel}>
                    {seg.type === 'walk'
                      ? `Walk ${(seg as any).duration} min`
                      : seg.type === 'transfer'
                      ? `Transfer ${(seg as any).duration} min`
                      : (seg as any).routeShortName}
                    {si < journey.segments.length - 1 && <span style={styles.segmentArrow}>→</span>}
                  </span>
                ))}
              </div>
              <div style={styles.journeyMeta}>
                <span style={styles.fareLabel}>{journey.fareLabel}</span>
                <span style={styles.walkLabel}>
                  {(journey.totalWalkDistance / 1000).toFixed(1)} km walk
                </span>
              </div>
            </button>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <button style={styles.backBtn} onClick={() => navigate('home')}>
          <ArrowLeft size={20} />
        </button>
        <h2 style={styles.headerTitle}>Plan Journey</h2>
      </div>

      <div style={styles.inputSection}>
        <div style={styles.inputRow}>
          <div style={styles.dotIndicator}>
            <div style={styles.greenDot} />
            <div style={styles.connectorLine} />
            <div style={styles.redDot} />
          </div>
          <div style={styles.inputs}>
            <div
              style={{ ...styles.inputWrap, ...(activeField === 'from' ? styles.inputWrapActive : {}) }}
              onClick={() => setActiveField('from')}
            >
              <input
                style={styles.input}
                placeholder="From"
                value={state.searchOrigin}
                onChange={(e) => { setSearchOrigin(e.target.value); setQuery(e.target.value); setActiveField('from'); }}
                onFocus={() => setActiveField('from')}
              />
              {state.searchOrigin && activeField === 'from' && (
                <button style={styles.clearBtn} onClick={() => { setSearchOrigin(''); setQuery(''); }}>
                  <X size={14} />
                </button>
              )}
            </div>
            <div
              style={{ ...styles.inputWrap, ...(activeField === 'to' ? styles.inputWrapActive : {}) }}
              onClick={() => setActiveField('to')}
            >
              <input
                style={styles.input}
                placeholder="To"
                value={state.searchDestination}
                onChange={(e) => { setSearchDestination(e.target.value); setQuery(e.target.value); setActiveField('to'); }}
                onFocus={() => setActiveField('to')}
              />
              {state.searchDestination && activeField === 'to' && (
                <button style={styles.clearBtn} onClick={() => { setSearchDestination(''); setQuery(''); }}>
                  <X size={14} />
                </button>
              )}
            </div>
          </div>
          <button style={styles.swapBtn} onClick={handleSwap} title="Swap">
            <ArrowUpDown size={18} />
          </button>
        </div>

        <div style={styles.optionsRow}>
          <div style={styles.leaveNow}>
            <Clock size={14} color="var(--color-text-muted)" />
            <span style={styles.leaveNowText}>Leave now</span>
          </div>
        </div>

        <button
          style={{
            ...styles.searchBtn,
            ...(state.searchOrigin && state.searchDestination ? {} : styles.searchBtnDisabled),
          }}
          onClick={handleSearch}
          disabled={!state.searchOrigin || !state.searchDestination}
        >
          <Search size={16} />
          <span>Find journeys</span>
        </button>
      </div>

      <div style={styles.resultsSection}>
        <div style={styles.resultsHeader}>
          <span style={styles.resultsLabel}>
            {query ? 'Search results' : 'Popular destinations'}
          </span>
        </div>
        <div style={styles.resultsList}>
          {filtered.map((result) => (
            <button
              key={result.id}
              style={styles.resultItem}
              onClick={() => handleSelect(result.name)}
              onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--color-surface-hover)'; }}
              onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
            >
              <div style={styles.resultIcon}>
                {iconForType(result.type)}
              </div>
              <div style={styles.resultInfo}>
                <span style={styles.resultName}>{result.name}</span>
                {result.subtitle && (
                  <span style={styles.resultSubtitle}>{result.subtitle}</span>
                )}
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
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
    background: 'var(--color-bg)',
    overflow: 'hidden',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    padding: '16px 20px',
    borderBottom: '1px solid var(--color-hairline)',
  },
  backBtn: {
    width: 36,
    height: 36,
    borderRadius: 'var(--radius-sm)',
    border: 'none',
    background: 'transparent',
    color: 'var(--color-text-primary)',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  headerTitle: {
    fontSize: 17,
    fontWeight: 600,
  },
  inputSection: {
    padding: '20px',
  },
  inputRow: {
    display: 'flex',
    gap: 12,
    alignItems: 'stretch',
  },
  dotIndicator: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 2,
    paddingTop: 8,
  },
  greenDot: {
    width: 10,
    height: 10,
    borderRadius: '50%',
    background: 'var(--color-accent-primary)',
    flexShrink: 0,
  },
  connectorLine: {
    width: 2,
    flex: 1,
    minHeight: 20,
    background: 'var(--color-border)',
  },
  redDot: {
    width: 10,
    height: 10,
    borderRadius: '50%',
    background: 'var(--color-error)',
    flexShrink: 0,
  },
  inputs: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    gap: 8,
  },
  inputWrap: {
    display: 'flex',
    alignItems: 'center',
    padding: '12px 16px',
    background: 'var(--color-surface)',
    borderRadius: 'var(--radius-md)',
    border: '1.5px solid var(--color-hairline)',
    transition: 'border-color var(--duration-fast) var(--ease-smooth)',
  },
  inputWrapActive: {
    borderColor: 'var(--color-accent-primary)',
  },
  input: {
    flex: 1,
    border: 'none',
    outline: 'none',
    fontSize: 15,
    fontFamily: 'var(--font-sans)',
    color: 'var(--color-text-primary)',
    background: 'transparent',
  },
  clearBtn: {
    width: 24,
    height: 24,
    borderRadius: '50%',
    border: 'none',
    background: 'var(--color-surface-hover)',
    color: 'var(--color-text-muted)',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  swapBtn: {
    width: 44,
    height: 44,
    borderRadius: 'var(--radius-md)',
    border: '1px solid var(--color-hairline)',
    background: 'var(--color-surface)',
    color: 'var(--color-text-secondary)',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    alignSelf: 'center',
    transition: 'all var(--duration-fast) var(--ease-smooth)',
    flexShrink: 0,
  },
  optionsRow: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    marginTop: 16,
  },
  leaveNow: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    padding: '8px 12px',
    background: 'var(--color-surface)',
    borderRadius: 'var(--radius-full)',
    border: '1px solid var(--color-hairline)',
  },
  leaveNowText: {
    fontSize: 13,
    color: 'var(--color-text-secondary)',
    fontWeight: 500,
  },
  searchBtn: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    width: '100%',
    marginTop: 16,
    padding: '14px 24px',
    background: 'var(--color-accent-primary)',
    color: '#FFFFFF',
    border: 'none',
    borderRadius: 'var(--radius-full)',
    fontSize: 15,
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'all var(--duration-fast) var(--ease-smooth)',
  },
  searchBtnDisabled: {
    opacity: 0.5,
    cursor: 'not-allowed',
  },
  resultsSection: {
    flex: 1,
    overflow: 'auto',
    borderTop: '1px solid var(--color-hairline)',
  },
  resultsHeader: {
    padding: '16px 20px 8px',
  },
  resultsLabel: {
    fontSize: 12,
    fontWeight: 600,
    color: 'var(--color-text-muted)',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.5px',
  },
  resultsList: {
    padding: '0 8px 8px',
  },
  resultItem: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    width: '100%',
    padding: '12px',
    border: 'none',
    background: 'transparent',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
    textAlign: 'left' as const,
    transition: 'background var(--duration-fast) var(--ease-smooth)',
  },
  resultIcon: {
    width: 36,
    height: 36,
    borderRadius: 'var(--radius-sm)',
    background: 'var(--color-surface-hover)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  resultInfo: {
    display: 'flex',
    flexDirection: 'column',
    gap: 2,
  },
  resultName: {
    fontSize: 14,
    fontWeight: 500,
    color: 'var(--color-text-primary)',
  },
  resultSubtitle: {
    fontSize: 12,
    color: 'var(--color-text-muted)',
  },
  summaryBar: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '12px 20px',
    background: 'var(--color-surface)',
    borderBottom: '1px solid var(--color-hairline)',
  },
  summaryText: {
    fontSize: 14,
    fontWeight: 500,
    color: 'var(--color-text-primary)',
  },
  demoTag: {
    fontSize: 10,
    fontWeight: 600,
    color: 'var(--color-text-muted)',
    padding: '3px 8px',
    background: 'var(--color-surface-hover)',
    borderRadius: 'var(--radius-full)',
    letterSpacing: '0.3px',
    textTransform: 'uppercase' as const,
  },
  journeyList: {
    flex: 1,
    overflow: 'auto',
    padding: '16px 20px',
    display: 'flex',
    flexDirection: 'column',
    gap: 12,
  },
  journeyCard: {
    display: 'flex',
    flexDirection: 'column',
    gap: 12,
    padding: 20,
    background: 'var(--color-surface)',
    borderRadius: 'var(--radius-md)',
    border: '1px solid var(--color-hairline)',
    cursor: 'pointer',
    textAlign: 'left' as const,
    transition: 'all var(--duration-fast) var(--ease-smooth)',
    animation: 'slideUp var(--duration-normal) var(--ease-spring) both',
  },
  journeyCardBest: {
    borderColor: 'var(--color-accent-primary)',
    boxShadow: '0 0 0 1px var(--color-accent-primary)',
  },
  journeyTop: {
    display: 'flex',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
  },
  journeyDuration: {
    display: 'flex',
    alignItems: 'baseline',
    gap: 3,
  },
  durationNum: {
    fontSize: 28,
    fontWeight: 700,
    color: 'var(--color-text-primary)',
    lineHeight: 1,
  },
  durationUnit: {
    fontSize: 14,
    fontWeight: 500,
    color: 'var(--color-text-muted)',
  },
  journeyTag: {
    fontSize: 10,
    fontWeight: 600,
    padding: '3px 10px',
    borderRadius: 'var(--radius-full)',
    textTransform: 'capitalize' as const,
    letterSpacing: '0.3px',
  },
  tagRecommended: {
    background: 'var(--color-accent-primary-muted)',
    color: 'var(--color-accent-primary)',
  },
  tagFastest: {
    background: '#FFF3CD',
    color: '#8B6914',
  },
  tagWalking: {
    background: 'var(--color-accent-secondary-muted)',
    color: 'var(--color-accent-secondary)',
  },
  journeySegments: {
    display: 'flex',
    flexWrap: 'wrap' as const,
    alignItems: 'center',
    gap: 4,
  },
  segmentLabel: {
    fontSize: 13,
    fontWeight: 500,
    color: 'var(--color-text-secondary)',
  },
  segmentArrow: {
    margin: '0 4px',
    color: 'var(--color-text-muted)',
  },
  journeyMeta: {
    display: 'flex',
    gap: 16,
    alignItems: 'center',
  },
  fareLabel: {
    fontSize: 14,
    fontWeight: 600,
    color: 'var(--color-accent-primary)',
  },
  walkLabel: {
    fontSize: 12,
    color: 'var(--color-text-muted)',
  },
};
