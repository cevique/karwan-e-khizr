import { useState, useEffect, useCallback } from 'react';
import { useApp } from '../App';
import { transitService } from '@shared/services/transit-service';
import type { ApiTicketResponse } from '@shared/types/api';
import { QRCodeSVG } from 'qrcode.react';
import { ArrowLeft, Ticket, Loader2, AlertCircle, LogIn, X } from 'lucide-react';

const STATUS_STYLE: Record<string, { bg: string; fg: string }> = {
  ACTIVE: { bg: 'var(--color-accent-primary-muted)', fg: 'var(--color-accent-primary)' },
  USED: { bg: 'var(--color-divider)', fg: 'var(--color-text-muted)' },
  EXPIRED: { bg: 'var(--color-divider)', fg: 'var(--color-text-muted)' },
  REVOKED: { bg: 'rgba(212,61,61,0.08)', fg: 'var(--color-error)' },
};

export function TicketsScreen() {
  const { auth, goBack, navigate } = useApp();
  const [tickets, setTickets] = useState<ApiTicketResponse[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [openTicket, setOpenTicket] = useState<ApiTicketResponse | null>(null);

  const load = useCallback(() => {
    if (!auth.token) return;
    setLoading(true);
    setError(null);
    transitService.listTickets(auth.token)
      .then(setTickets)
      .catch(() => setError('Could not load your tickets. Please try again.'))
      .finally(() => setLoading(false));
  }, [auth.token]);

  useEffect(() => { load(); }, [load]);

  if (!auth.user) {
    return (
      <div style={styles.container}>
        <div style={styles.header}>
          <button style={styles.backBtn} onClick={goBack}><ArrowLeft size={20} /></button>
          <h2 style={styles.headerTitle}>My Tickets</h2>
        </div>
        <div style={styles.signInPrompt}>
          <Ticket size={40} color="var(--color-text-muted)" />
          <p style={styles.signInText}>Sign in to view and manage your tickets.</p>
          <button style={styles.signInBtn} onClick={() => navigate('auth')}>
            <LogIn size={16} />
            <span>Sign in</span>
          </button>
        </div>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <button style={styles.backBtn} onClick={goBack}><ArrowLeft size={20} /></button>
        <h2 style={styles.headerTitle}>My Tickets</h2>
      </div>

      <div style={styles.content}>
        {loading && (
          <div style={styles.stateMessage}>
            <Loader2 size={20} className="spin" />
            <span>Loading your tickets…</span>
          </div>
        )}
        {!loading && error && (
          <div style={styles.stateMessage}>
            <AlertCircle size={20} color="var(--color-error)" />
            <span>{error}</span>
          </div>
        )}
        {!loading && !error && tickets && tickets.length === 0 && (
          <div style={styles.stateMessage}>
            <Ticket size={32} color="var(--color-text-muted)" />
            <span>No tickets yet. Plan a journey and buy one from the journey details.</span>
          </div>
        )}
        {!loading && !error && tickets && tickets.length > 0 && (
          <div style={styles.ticketList}>
            {tickets.map((t) => {
              const statusStyle = STATUS_STYLE[t.status] ?? STATUS_STYLE.USED;
              return (
                <button key={t.id} style={styles.ticketCard} onClick={() => setOpenTicket(t)}>
                  <div style={styles.ticketCardTop}>
                    <span style={styles.ticketId}>Ticket #{t.id}</span>
                    <span style={{ ...styles.statusBadge, background: statusStyle.bg, color: statusStyle.fg }}>
                      {t.status.charAt(0) + t.status.slice(1).toLowerCase()}
                    </span>
                  </div>
                  <div style={styles.ticketCardBottom}>
                    <span style={styles.ticketFare}>{t.currency} {t.fare_charged.toFixed(2)}</span>
                    <span style={styles.ticketDate}>{new Date(t.created_at).toLocaleDateString()}</span>
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </div>

      {openTicket && (
        <div style={styles.modalOverlay} onClick={() => setOpenTicket(null)}>
          <div style={styles.modal} onClick={(e) => e.stopPropagation()}>
            <button style={styles.modalClose} onClick={() => setOpenTicket(null)}><X size={18} /></button>
            <span style={styles.modalTitle}>Ticket #{openTicket.id}</span>
            <div style={styles.qrWrap}>
              <QRCodeSVG value={openTicket.qr_payload} size={200} level="M" />
            </div>
            <span style={{
              ...styles.statusBadge,
              ...(STATUS_STYLE[openTicket.status] ?? STATUS_STYLE.USED),
              background: (STATUS_STYLE[openTicket.status] ?? STATUS_STYLE.USED).bg,
              color: (STATUS_STYLE[openTicket.status] ?? STATUS_STYLE.USED).fg,
            }}>
              {openTicket.status.charAt(0) + openTicket.status.slice(1).toLowerCase()}
            </span>
            <span style={styles.modalFare}>{openTicket.currency} {openTicket.fare_charged.toFixed(2)}</span>
            <span style={styles.modalMeta}>
              Purchased {new Date(openTicket.created_at).toLocaleString()}
            </span>
            {openTicket.expires_at && (
              <span style={styles.modalMeta}>
                Expires {new Date(openTicket.expires_at).toLocaleString()}
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    flex: 1, display: 'flex', flexDirection: 'column', height: '100%',
    background: 'var(--color-bg)', maxWidth: 'var(--content-max-width)',
    margin: '0 auto', width: '100%', position: 'relative',
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
  content: { flex: 1, overflow: 'auto', padding: '16px 20px 32px' },
  stateMessage: {
    display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10,
    padding: '48px 20px', color: 'var(--color-text-muted)', fontSize: 14, textAlign: 'center' as const,
  },
  signInPrompt: {
    flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center',
    justifyContent: 'center', gap: 14, padding: 32, textAlign: 'center' as const,
  },
  signInText: { fontSize: 14, color: 'var(--color-text-muted)', maxWidth: 240 },
  signInBtn: {
    display: 'flex', alignItems: 'center', gap: 8, padding: '12px 24px',
    background: 'var(--color-accent-primary)', color: '#FFFFFF',
    border: 'none', borderRadius: 'var(--radius-full)',
    fontSize: 14, fontWeight: 600, cursor: 'pointer',
  },
  ticketList: { display: 'flex', flexDirection: 'column', gap: 10 },
  ticketCard: {
    display: 'flex', flexDirection: 'column', gap: 8, padding: '16px 18px',
    background: 'var(--color-surface)', borderRadius: 'var(--radius-md)',
    border: '1px solid var(--color-hairline)', cursor: 'pointer', textAlign: 'left' as const,
  },
  ticketCardTop: { display: 'flex', alignItems: 'center', justifyContent: 'space-between' },
  ticketId: { fontSize: 14, fontWeight: 600, color: 'var(--color-text-primary)' },
  statusBadge: {
    fontSize: 11, fontWeight: 600, padding: '3px 10px', borderRadius: 'var(--radius-full)',
  },
  ticketCardBottom: { display: 'flex', alignItems: 'center', justifyContent: 'space-between' },
  ticketFare: { fontSize: 13, fontWeight: 600, color: 'var(--color-accent-primary)' },
  ticketDate: { fontSize: 12, color: 'var(--color-text-muted)' },
  modalOverlay: {
    position: 'absolute', inset: 0, background: 'var(--color-overlay)',
    display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 10,
  },
  modal: {
    position: 'relative', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10,
    background: 'var(--color-surface)', borderRadius: 'var(--radius-lg)',
    padding: '32px 28px', boxShadow: 'var(--shadow-3)', maxWidth: 300,
  },
  modalClose: {
    position: 'absolute', top: 12, right: 12, width: 28, height: 28,
    borderRadius: 'var(--radius-sm)', border: 'none', background: 'var(--color-surface-hover)',
    color: 'var(--color-text-secondary)', cursor: 'pointer',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
  },
  modalTitle: { fontSize: 15, fontWeight: 700, color: 'var(--color-text-primary)' },
  qrWrap: { padding: 16, background: '#FFFFFF', borderRadius: 'var(--radius-md)', margin: '8px 0' },
  modalFare: { fontSize: 18, fontWeight: 700, color: 'var(--color-accent-primary)' },
  modalMeta: { fontSize: 12, color: 'var(--color-text-muted)', textAlign: 'center' as const },
};
