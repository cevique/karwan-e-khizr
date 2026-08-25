import { useApp } from '../../App';
import type { Screen } from '../../App';
import { Home, Route, Heart, User } from 'lucide-react';

const navItems: { id: Screen; label: string; icon: typeof Home }[] = [
  { id: 'home', label: 'Home', icon: Home },
  { id: 'routes', label: 'Routes', icon: Route },
  { id: 'saved', label: 'Saved', icon: Heart },
  { id: 'settings', label: 'Profile', icon: User },
];

export function MobileNav() {
  const { state, navigate } = useApp();
  const activeTab = state.screen === 'journey-detail' ? 'routes' : state.screen === 'search' ? 'home' : state.screen;

  return (
    <nav style={styles.nav}>
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
          >
            <Icon size={22} strokeWidth={isActive ? 2.2 : 1.5} />
            <span style={{
              ...styles.label,
              ...(isActive ? styles.labelActive : {}),
            }}>{label}</span>
          </button>
        );
      })}
    </nav>
  );
}

const styles: Record<string, React.CSSProperties> = {
  nav: {
    display: 'flex',
    height: 60,
    background: 'var(--color-surface)',
    borderTop: '1px solid var(--color-hairline)',
    paddingBottom: 'env(safe-area-inset-bottom, 0px)',
  },
  item: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '2px',
    border: 'none',
    background: 'transparent',
    color: 'var(--color-text-muted)',
    cursor: 'pointer',
    transition: 'color var(--duration-fast) var(--ease-smooth)',
    WebkitTapHighlightColor: 'transparent',
  },
  itemActive: {
    color: 'var(--color-accent-primary)',
  },
  label: {
    fontSize: 10,
    fontWeight: 500,
    lineHeight: 1,
  },
  labelActive: {
    fontWeight: 600,
  },
};
