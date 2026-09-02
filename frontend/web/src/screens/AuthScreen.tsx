import { useState } from 'react';
import { useApp } from '../App';
import { ArrowLeft, Mail, Lock, User, Loader2 } from 'lucide-react';

export function AuthScreen() {
  const { auth, goBack } = useApp();
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    auth.clearError();
    try {
      if (mode === 'login') {
        await auth.login(email, password);
      } else {
        await auth.register(email, password, fullName || undefined);
      }
      goBack();
    } catch {
      // auth.error is already set by the context; stay on the form.
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <button style={styles.backBtn} onClick={goBack}>
          <ArrowLeft size={20} />
        </button>
        <h2 style={styles.headerTitle}>{mode === 'login' ? 'Sign in' : 'Create account'}</h2>
      </div>

      <div style={styles.content}>
        <div style={styles.brandSection}>
          <div style={styles.brandIcon}>
            <span style={styles.brandEmoji}>🚌</span>
          </div>
          <h3 style={styles.brandName}>Karwan-e-Khizr</h3>
          <p style={styles.brandSubtitle}>
            {mode === 'login' ? 'Sign in to buy and manage tickets' : 'Create an account to buy tickets'}
          </p>
        </div>

        <form style={styles.form} onSubmit={handleSubmit}>
          {mode === 'register' && (
            <label style={styles.field}>
              <span style={styles.fieldLabel}>Full name</span>
              <div style={styles.inputWrap}>
                <User size={16} color="var(--color-text-muted)" />
                <input
                  style={styles.input}
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="Your name"
                  autoComplete="name"
                />
              </div>
            </label>
          )}

          <label style={styles.field}>
            <span style={styles.fieldLabel}>Email</span>
            <div style={styles.inputWrap}>
              <Mail size={16} color="var(--color-text-muted)" />
              <input
                style={styles.input}
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                autoComplete="email"
                required
              />
            </div>
          </label>

          <label style={styles.field}>
            <span style={styles.fieldLabel}>Password</span>
            <div style={styles.inputWrap}>
              <Lock size={16} color="var(--color-text-muted)" />
              <input
                style={styles.input}
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                minLength={8}
                required
              />
            </div>
          </label>

          {auth.error && <div style={styles.errorBox}>{auth.error}</div>}

          <button style={styles.submitBtn} type="submit" disabled={auth.loading}>
            {auth.loading ? (
              <Loader2 size={16} className="spin" />
            ) : (
              <span>{mode === 'login' ? 'Sign in' : 'Create account'}</span>
            )}
          </button>
        </form>

        <button
          style={styles.switchModeBtn}
          onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); auth.clearError(); }}
        >
          {mode === 'login' ? "Don't have an account? Sign up" : 'Already have an account? Sign in'}
        </button>
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
    display: 'flex', alignItems: 'center', gap: 12, padding: '16px 20px',
    borderBottom: '1px solid var(--color-hairline)',
  },
  backBtn: {
    width: 36, height: 36, borderRadius: 'var(--radius-sm)', border: 'none',
    background: 'transparent', color: 'var(--color-text-primary)', cursor: 'pointer',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
  },
  headerTitle: { fontSize: 15, fontWeight: 600 },
  content: { flex: 1, overflow: 'auto', padding: '0 20px 32px' },
  brandSection: {
    display: 'flex', flexDirection: 'column', alignItems: 'center',
    padding: '32px 0 24px', gap: 4, textAlign: 'center' as const,
  },
  brandIcon: {
    width: 64, height: 64, borderRadius: 'var(--radius-lg)',
    background: 'var(--color-accent-primary-muted)',
    display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 8,
  },
  brandEmoji: { fontSize: 28 },
  brandName: { fontSize: 20, fontWeight: 700, color: 'var(--color-text-primary)' },
  brandSubtitle: { fontSize: 13, color: 'var(--color-text-muted)', marginTop: 4, maxWidth: 260 },
  form: { display: 'flex', flexDirection: 'column', gap: 14, marginTop: 8 },
  field: { display: 'flex', flexDirection: 'column', gap: 6 },
  fieldLabel: { fontSize: 12, fontWeight: 600, color: 'var(--color-text-secondary)' },
  inputWrap: {
    display: 'flex', alignItems: 'center', gap: 10, padding: '12px 14px',
    background: 'var(--color-surface)', borderRadius: 'var(--radius-md)',
    border: '1px solid var(--color-hairline)',
  },
  input: {
    flex: 1, border: 'none', outline: 'none', background: 'transparent',
    fontSize: 14, color: 'var(--color-text-primary)', fontFamily: 'var(--font-sans)',
  },
  errorBox: {
    padding: '10px 14px', borderRadius: 'var(--radius-md)',
    background: 'rgba(212,61,61,0.08)', color: 'var(--color-error)',
    fontSize: 13, fontWeight: 500,
  },
  submitBtn: {
    display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
    padding: '14px 24px', marginTop: 4,
    background: 'var(--color-accent-primary)', color: '#FFFFFF',
    border: 'none', borderRadius: 'var(--radius-full)',
    fontSize: 15, fontWeight: 600, cursor: 'pointer',
  },
  switchModeBtn: {
    display: 'block', width: '100%', textAlign: 'center' as const, marginTop: 20,
    border: 'none', background: 'none', color: 'var(--color-accent-primary)',
    fontSize: 13, fontWeight: 500, cursor: 'pointer', padding: 8,
  },
};
