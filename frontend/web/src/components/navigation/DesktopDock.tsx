import { useApp } from '../../App';
import type { Screen } from '../../App';
import { Home, Map, Heart, Settings, Route } from 'lucide-react';

const navItems: { id: Screen; label: string; icon: typeof Home }[] = [
  { id: 'home', label: 'Home', icon: Home },
  { id: 'routes', label: 'Routes', icon: Route },
  { id: 'saved', label: 'Saved', icon: Heart },
  { id: 'settings', label: 'Settings', icon: Settings },
];

export function DesktopDock() {
  const { state, navigate } = useApp();
  const activeTab = state.screen === 'journey-detail' ? 'routes'
    : state.screen === 'search' ? 'home'
    : state.screen === 'auth' || state.screen === 'tickets' ? 'settings'
    : state.screen;

  return (
    <nav style={styles.dock}>
      <div style={styles.brand}>
        <div style={styles.brandIcon}>
          <Map size={24} strokeWidth={1.5} />
        </div>
        <span style={styles.brandLabel}>KEK</span>
      </div>

      <div style={styles.divider} />

      <div style={styles.items}>
        {navItems.map(({ id, label, icon: Icon }) => {
          const isActive = activeTab === id;
          return (
            <button
              key={id}
              onClick={() => navigate(id)}
              style={{
                ...styles.item,
                ...(isActive ? styles.itemActive : {}),
              }}
              onMouseEnter={(e) => {
                if (!isActive) e.currentTarget.style.background = 'var(--color-surface-hover)';
              }}
              onMouseLeave={(e) => {
                if (!isActive) e.currentTarget.style.background = 'transparent';
              }}
              title={label}
            >
              <Icon size={20} strokeWidth={isActive ? 2 : 1.5} />
              <span style={styles.itemLabel}>{label}</span>
            </button>
          );
        })}
      </div>
    </nav>
  );
}

const styles: Record<string, React.CSSProperties> = {
  dock: {
    width: 'var(--dock-width)',
    height: '100%',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    padding: '20px 0',
    background: 'var(--color-surface)',
    borderRight: '1px solid var(--color-hairline)',
    gap: '8px',
    flexShrink: 0,
  },
  brand: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '4px',
    marginBottom: '8px',
  },
  brandIcon: {
    width: 40,
    height: 40,
    borderRadius: 'var(--radius-md)',
    background: 'var(--color-accent-primary)',
    color: 'var(--color-text-inverse)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  brandLabel: {
    fontSize: 9,
    fontWeight: 600,
    letterSpacing: '0.5px',
    color: 'var(--color-text-muted)',
    textTransform: 'uppercase' as const,
  },
  divider: {
    width: 32,
    height: 1,
    background: 'var(--color-hairline)',
    marginBottom: '8px',
  },
  items: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '4px',
    flex: 1,
  },
  item: {
    width: 52,
    height: 52,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '2px',
    borderRadius: 'var(--radius-md)',
    border: 'none',
    background: 'transparent',
    color: 'var(--color-text-secondary)',
    cursor: 'pointer',
    transition: 'all var(--duration-fast) var(--ease-smooth)',
  },
  itemActive: {
    background: 'var(--color-accent-primary-muted)',
    color: 'var(--color-accent-primary)',
  },
  itemLabel: {
    fontSize: 10,
    fontWeight: 500,
    lineHeight: 1,
  },
};
