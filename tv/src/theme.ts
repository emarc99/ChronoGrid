export const colors = {
  bg: '#0b0f14',
  panel: '#121821',
  panelEdge: '#1f2a36',
  text: '#e8eef5',
  muted: '#8a98a8',
  accent: '#3ee0b0',
  warn: '#ffb547',
  danger: '#ff5d5d',
  add: '#3ee0b0',
  del: '#ff6b6b',
  focus: '#ffffff',
};

export const mono = 'monospace';

// The device clock may run in UTC; show the household's time, as reported by the server.
let utcOffset = 0;
export function setUtcOffset(seconds: number) {
  utcOffset = seconds;
}

function local(ts: number): Date {
  return new Date((ts + utcOffset) * 1000);
}

export function clock(ts: number): string {
  const d = local(ts);
  const h = d.getUTCHours();
  const m = d.getUTCMinutes().toString().padStart(2, '0');
  return `${((h + 11) % 12) + 1}:${m} ${h < 12 ? 'AM' : 'PM'}`;
}

export function hourLabel(ts: number): string {
  const h = local(ts).getUTCHours();
  return `${((h + 11) % 12) + 1}${h < 12 ? 'a' : 'p'}`;
}

export function ago(ts: number, now = Date.now() / 1000): string {
  const s = Math.max(0, now - ts);
  if (s < 60) {
    return 'just now';
  }
  if (s < 3600) {
    return `${Math.round(s / 60)} min ago`;
  }
  return `${Math.round(s / 3600)} h ago`;
}
