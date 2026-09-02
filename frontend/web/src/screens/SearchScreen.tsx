import { useState } from 'react';
import { useApp } from '../App';
import { Search, ArrowLeft, MapPin, TrainFront, Building2, X, ArrowUpDown, Clock, Loader2, AlertCircle, Sparkles, Send } from 'lucide-react';
import { mockSearchResults } from '@shared/index';
import type { Journey } from '@shared/types';
import type { AssistantResult } from '@shared/services/transit-service';
import { useSearchResults, useJourneySearch } from '@shared/hooks/useTransitData';
import { AmbiguousLocationError, NoRouteFoundError, transitService } from '@shared/services/transit-service';

function JourneyList({ journeys, onSelect }: { journeys: Journey[]; onSelect: (j: Journey) => void }) {
  return (
    <div style={styles.journeyList}>
      {journeys.map((journey, i) => (
        <button
          key={journey.id}
          style={{
            ...styles.journeyCard,
            animationDelay: `${i * 80}ms`,
            ...(journey.tag === 'recommended' ? styles.journeyCardBest : {}),
          }}
          onClick={() => onSelect(journey)}
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
                  ? `Walk ${seg.duration} min`
                  : seg.type === 'transfer'
                  ? `Transfer ${seg.duration} min`
                  : seg.routeShortName}
                {si < journey.segments.length - 1 && <span style={styles.segmentArrow}>→</span>}
              </span>
            ))}
          </div>
          <div style={styles.journeyMeta}>
            <span style={styles.fareLabel}>{journey.fareLabel}</span>
            <span style={styles.walkLabel}>
              {(journey.totalWalkDistance / 1000).toFixed(1)} km walk
              {journey.transferCount != null && journey.transferCount > 0
                ? ` · ${journey.transferCount} transfer${journey.transferCount > 1 ? 's' : ''}`
                : ''}
            </span>
          </div>
        </button>
      ))}
    </div>
  );
}

export function SearchScreen() {
  const { state, navigate, setSearchOrigin, setSearchDestination, selectJourney, transit, auth } = useApp();
  const [query, setQuery] = useState('');
  const [activeField, setActiveField] = useState<'from' | 'to'>('to');
  const [showJourneys, setShowJourneys] = useState(false);

  // "Ask" mode: free-text natural-language search via the AI assistant
  const [askMode, setAskMode] = useState(false);
  const [askQuery, setAskQuery] = useState('');
  const [askLoading, setAskLoading] = useState(false);
  const [askResult, setAskResult] = useState<AssistantResult | null>(null);
  const [askErrorMsg, setAskErrorMsg] = useState<string | null>(null);

  // Use the service layer for search results
  const { data: searchResults } = useSearchResults(query);
  // Fall back to full list when query is empty
  const filtered = query.length > 0 ? searchResults : mockSearchResults;

  const {
    data: journeys,
    loading: journeysLoading,
    error: journeysError,
  } = useJourneySearch(state.searchOrigin, state.searchDestination, transit.routes, transit.stops, showJourneys);

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

  const handleAsk = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!askQuery.trim() || askLoading) return;
    setAskLoading(true);
    setAskErrorMsg(null);
    setAskResult(null);
    try {
      const result = await transitService.askAssistant(askQuery, transit.routes, transit.stops, auth.token ?? undefined);
      setAskResult(result);
    } catch {
      setAskErrorMsg("Sorry, I couldn't reach the assistant. Please try again.");
    } finally {
      setAskLoading(false);
    }
  };

  const iconForType = (type: string) => {
    if (type === 'stop') return <MapPin size={16} color="var(--color-accent-secondary)" />;
    if (type === 'station') return <TrainFront size={16} color="var(--color-accent-primary)" />;
    return <Building2 size={16} color="var(--color-text-muted)" />;
  };

  if (showJourneys) {
    let errorMessage: string | null = null;
    if (journeysError instanceof AmbiguousLocationError) {
      const candidateNames = journeysError.candidates.map((c) => c.name).join(', ');
      errorMessage = `"${journeysError.field === 'origin' ? state.searchOrigin : state.searchDestination}" could mean several places: ${candidateNames}. Try being more specific.`;
    } else if (journeysError instanceof NoRouteFoundError) {
      errorMessage = journeysError.message || 'No route found between these two places.';
    } else if (journeysError) {
      errorMessage = 'Something went wrong finding journeys. Please try again.';
    }

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
        </div>
        {journeysLoading && (
          <div style={styles.stateMessage}>
            <Loader2 size={20} className="spin" />
            <span>Finding journeys…</span>
          </div>
        )}
        {!journeysLoading && errorMessage && (
          <div style={styles.stateMessage}>
            <AlertCircle size={20} color="var(--color-error)" />
            <span>{errorMessage}</span>
          </div>
        )}
        {!journeysLoading && !errorMessage && journeys && journeys.length === 0 && (
          <div style={styles.stateMessage}>
            <span>No journeys found.</span>
          </div>
        )}
        {!journeysLoading && !errorMessage && journeys && journeys.length > 0 && (
          <JourneyList journeys={journeys} onSelect={selectJourney} />
        )}
      </div>
    );
  }

  if (askMode) {
    return (
      <div style={styles.container}>
        <div style={styles.header}>
          <button style={styles.backBtn} onClick={() => setAskMode(false)}>
            <ArrowLeft size={20} />
          </button>
          <h2 style={styles.headerTitle}>Ask Karwan-e-Khizr</h2>
        </div>

        <form style={styles.askForm} onSubmit={handleAsk}>
          <div style={styles.askInputWrap}>
            <Sparkles size={16} color="var(--color-accent-primary)" />
            <input
              style={styles.input}
              placeholder="e.g. how do I get from Saddar to PIMS Hospital?"
              value={askQuery}
              onChange={(e) => setAskQuery(e.target.value)}
              autoFocus
            />
          </div>
          <button style={styles.askSubmitBtn} type="submit" disabled={askLoading || !askQuery.trim()}>
            {askLoading ? <Loader2 size={16} className="spin" /> : <Send size={16} />}
          </button>
        </form>

        <div style={styles.askResults}>
          {askLoading && (
            <div style={styles.stateMessage}>
              <Loader2 size={20} className="spin" />
              <span>Thinking…</span>
            </div>
          )}
          {!askLoading && askErrorMsg && (
            <div style={styles.stateMessage}>
              <AlertCircle size={20} color="var(--color-error)" />
              <span>{askErrorMsg}</span>
            </div>
          )}
          {!askLoading && askResult && (
            <>
              <div style={styles.replyBubble}>{askResult.reply}</div>
              {askResult.clarification && askResult.clarification.candidateNames.length > 0 && (
                <div style={styles.clarificationBox}>
                  <span style={styles.clarificationLabel}>Did you mean:</span>
                  <div style={styles.clarificationChips}>
                    {askResult.clarification.candidateNames.map((name) => (
                      <button
                        key={name}
                        style={styles.clarificationChip}
                        onClick={() => setAskQuery((q) => `${q} (${name})`)}
                      >
                        {name}
                      </button>
                    ))}
                  </div>
                </div>
              )}
              {askResult.journeys && askResult.journeys.length > 0 && (
                <JourneyList journeys={askResult.journeys} onSelect={selectJourney} />
              )}
            </>
          )}
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
        <button style={styles.askToggleBtn} onClick={() => setAskMode(true)} title="Ask in plain language">
          <Sparkles size={16} />
          <span>Ask</span>
        </button>
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
    flex: 1,
  },
  askToggleBtn: {
    display: 'flex', alignItems: 'center', gap: 6, padding: '8px 14px',
    background: 'var(--color-accent-primary-muted)', color: 'var(--color-accent-primary)',
    border: 'none', borderRadius: 'var(--radius-full)', fontSize: 13, fontWeight: 600, cursor: 'pointer',
  },
  askForm: {
    display: 'flex', alignItems: 'center', gap: 10, padding: '16px 20px',
    borderBottom: '1px solid var(--color-hairline)',
  },
  askInputWrap: {
    flex: 1, display: 'flex', alignItems: 'center', gap: 10, padding: '12px 16px',
    background: 'var(--color-surface)', borderRadius: 'var(--radius-md)',
    border: '1.5px solid var(--color-hairline)',
  },
  askSubmitBtn: {
    width: 44, height: 44, borderRadius: 'var(--radius-md)', border: 'none',
    background: 'var(--color-accent-primary)', color: '#FFFFFF', cursor: 'pointer',
    display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
  },
  askResults: { flex: 1, overflow: 'auto', padding: '16px 20px' },
  replyBubble: {
    padding: '14px 16px', background: 'var(--color-surface)',
    borderRadius: 'var(--radius-md)', border: '1px solid var(--color-hairline)',
    fontSize: 14, color: 'var(--color-text-primary)', lineHeight: 1.5, marginBottom: 12,
  },
  clarificationBox: { marginBottom: 12 },
  clarificationLabel: { fontSize: 12, color: 'var(--color-text-muted)', fontWeight: 600 },
  clarificationChips: { display: 'flex', flexWrap: 'wrap' as const, gap: 6, marginTop: 6 },
  clarificationChip: {
    padding: '6px 12px', borderRadius: 'var(--radius-full)',
    border: '1px solid var(--color-hairline)', background: 'var(--color-surface)',
    fontSize: 12, fontWeight: 500, color: 'var(--color-text-primary)', cursor: 'pointer',
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
  stateMessage: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    padding: '24px 20px',
    color: 'var(--color-text-muted)',
    fontSize: 14,
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
