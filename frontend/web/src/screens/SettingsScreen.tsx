import { useApp } from '../App';
import { Settings, Globe, Bell, Moon, Shield, Info, LogIn, LogOut, Ticket, UserCircle } from 'lucide-react';

export function SettingsScreen() {
  const { auth, navigate } = useApp();

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h2 style={styles.title}>Settings</h2>
      </div>
      <div style={styles.content}>
        <div style={styles.brandSection}>
          <div style={styles.brandIcon}>
            <span style={styles.brandEmoji}>🚌</span>
          </div>
          <h3 style={styles.brandName}>Karwan-e-Khizr</h3>
          <span className="urdu" style={styles.brandUrdu}>کاروانِ خِضر</span>
          <span style={styles.version}>v0.1.0 — Frontend Prototype</span>
        </div>

        <div style={styles.section}>
          <h4 style={styles.sectionTitle}>Account</h4>
          {auth.user ? (
            <>
              <div style={styles.settingRow}>
                <UserCircle size={18} color="var(--color-text-secondary)" />
                <div style={styles.settingInfo}>
                  <span style={styles.settingLabel}>{auth.user.full_name ?? 'Signed in'}</span>
                  <span style={styles.settingValue}>{auth.user.email}</span>
                </div>
              </div>
              <button style={styles.settingRowBtn} onClick={() => navigate('tickets')}>
                <Ticket size={18} color="var(--color-text-secondary)" />
                <div style={styles.settingInfo}>
                  <span style={styles.settingLabel}>My Tickets</span>
                </div>
              </button>
              <button style={styles.settingRowBtn} onClick={auth.logout}>
                <LogOut size={18} color="var(--color-error)" />
                <div style={styles.settingInfo}>
                  <span style={{ ...styles.settingLabel, color: 'var(--color-error)' }}>Sign out</span>
                </div>
              </button>
            </>
          ) : (
            <button style={styles.settingRowBtn} onClick={() => navigate('auth')}>
              <LogIn size={18} color="var(--color-accent-primary)" />
              <div style={styles.settingInfo}>
                <span style={{ ...styles.settingLabel, color: 'var(--color-accent-primary)' }}>Sign in</span>
                <span style={styles.settingValue}>Buy and manage tickets</span>
              </div>
            </button>
          )}
        </div>

        <div style={styles.section}>
          <h4 style={styles.sectionTitle}>Preferences</h4>
          <div style={styles.settingRow}>
            <Globe size={18} color="var(--color-text-secondary)" />
            <div style={styles.settingInfo}>
              <span style={styles.settingLabel}>Language</span>
              <span style={styles.settingValue}>English</span>
            </div>
          </div>
          <div style={styles.settingRow}>
            <Moon size={18} color="var(--color-text-secondary)" />
            <div style={styles.settingInfo}>
              <span style={styles.settingLabel}>Theme</span>
              <span style={styles.settingValue}>System</span>
            </div>
          </div>
          <div style={styles.settingRow}>
            <Bell size={18} color="var(--color-text-secondary)" />
            <div style={styles.settingInfo}>
              <span style={styles.settingLabel}>Notifications</span>
              <span style={styles.settingValue}>Off</span>
            </div>
          </div>
        </div>

        <div style={styles.section}>
          <h4 style={styles.sectionTitle}>About</h4>
          <div style={styles.settingRow}>
            <Shield size={18} color="var(--color-text-secondary)" />
            <div style={styles.settingInfo}>
              <span style={styles.settingLabel}>Privacy Policy</span>
            </div>
          </div>
          <div style={styles.settingRow}>
            <Info size={18} color="var(--color-text-secondary)" />
            <div style={styles.settingInfo}>
              <span style={styles.settingLabel}>About Karwan-e-Khizr</span>
              <span style={styles.settingValue}>Islamabad–Rawalpindi Transit</span>
            </div>
          </div>
        </div>

        <div style={styles.disclaimer}>
          <p>This is a demo prototype. All transit data shown is simulated for demonstration purposes only.</p>
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
    padding: '20px 20px 12px', borderBottom: '1px solid var(--color-hairline)',
  },
  title: { fontSize: 22, fontWeight: 600 },
  content: { flex: 1, overflow: 'auto', padding: '0 20px 32px' },
  brandSection: {
    display: 'flex', flexDirection: 'column', alignItems: 'center',
    padding: '32px 0 24px', gap: 4,
  },
  brandIcon: {
    width: 64, height: 64, borderRadius: 'var(--radius-lg)',
    background: 'var(--color-accent-primary-muted)',
    display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 8,
  },
  brandEmoji: { fontSize: 28 },
  brandName: { fontSize: 20, fontWeight: 700, color: 'var(--color-text-primary)' },
  brandUrdu: { fontSize: 16, color: 'var(--color-text-secondary)' },
  version: { fontSize: 12, color: 'var(--color-text-muted)', marginTop: 4 },
  section: { padding: '8px 0' },
  sectionTitle: {
    fontSize: 12, fontWeight: 600, color: 'var(--color-text-muted)',
    textTransform: 'uppercase' as const, letterSpacing: '0.5px',
    padding: '8px 0', marginBottom: 4,
  },
  settingRow: {
    display: 'flex', alignItems: 'center', gap: 14, padding: '14px 16px',
    background: 'var(--color-surface)', borderRadius: 'var(--radius-md)',
    marginBottom: 6, border: '1px solid var(--color-hairline)',
  },
  settingRowBtn: {
    display: 'flex', alignItems: 'center', gap: 14, padding: '14px 16px',
    background: 'var(--color-surface)', borderRadius: 'var(--radius-md)',
    marginBottom: 6, border: '1px solid var(--color-hairline)',
    width: '100%', textAlign: 'left' as const, cursor: 'pointer',
  },
  settingInfo: { flex: 1, display: 'flex', flexDirection: 'column', gap: 1 },
  settingLabel: { fontSize: 14, fontWeight: 500, color: 'var(--color-text-primary)' },
  settingValue: { fontSize: 12, color: 'var(--color-text-muted)' },
  disclaimer: {
    marginTop: 24, padding: 16,
    background: 'var(--color-accent-primary-muted)',
    borderRadius: 'var(--radius-md)',
    fontSize: 12, color: 'var(--color-text-secondary)', lineHeight: 1.6, textAlign: 'center' as const,
  },
};
