import {useEffect, useRef} from 'react';
import {SERVER, WS_URL} from './config';

export type BBox = [number, number, number, number];

export interface LedgerEvent {
  id: number;
  ts: number;
  kind: string;
  label: string;
  zone_id: string | null;
  zone_name: string;
  bbox: BBox | null;
}

export interface Zone {
  id: string;
  name: string;
  polygon: [number, number][];
  objects: string[];
  presence: {present: boolean; since: number | null};
}

export interface Alert {
  id: number;
  ts: number;
  severity: 'info' | 'warning' | 'critical';
  title: string;
  body: string;
  status: 'open' | 'snoozed' | 'resolved';
  evidence: string[];
}

export interface Rule {
  id: number;
  status: 'proposed' | 'active' | 'rejected' | 'disabled';
  source_text: string | null;
  spec: {
    name: string;
    message: string;
    severity: string;
    cooldown_seconds: number;
    when: Array<Record<string, any> & {type: string}>;
  };
}

export interface State {
  zones: Zone[];
  alerts: Alert[];
  rules: Rule[];
  recent: LedgerEvent[];
  now: number;
  utc_offset?: number;
}

export interface Grid {
  hours: number[];
  zones: string[];
  counts: Record<string, number[]>;
}

export type ScreenView = 'rewind' | 'log' | 'status' | 'diff' | 'commit' | 'rule_pr';

export type ScreenMessage =
  | {type: 'hello'}
  | {type: 'screen'; view: ScreenView; data: any}
  | {type: 'alert' | 'alert_resolved' | 'alert_snoozed'; alert: Alert}
  | {type: 'rule_updated'; rule: Rule}
  | {type: 'event'; event: LedgerEvent}
  | {type: 'appliance'; appliance: unknown}
  | {type: 'utterance'; text: string}
  | {type: 'assistant'; text: string; reply: string; tools: {tool: string; input: Record<string, unknown>}[]};

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    throw new Error(`${res.status}`);
  }
  return (await res.json()) as T;
}

export const api = {
  state: () => fetch(`${SERVER}/api/state`).then((r) => json<State>(r)),
  grid: (hours = 8) => fetch(`${SERVER}/api/grid?hours=${hours}`).then((r) => json<Grid>(r)),
  events: (zoneId: string, since: number, until: number) =>
    fetch(`${SERVER}/api/events?zone_id=${zoneId}&since=${since}&until=${until}&limit=20`).then((r) =>
      json<LedgerEvent[]>(r),
    ),
  ruleAction: (id: number, action: 'approve' | 'reject') =>
    fetch(`${SERVER}/api/rules/${id}/${action}`, {method: 'POST'}).then((r) => json<Rule>(r)),
  snooze: (id: number, minutes = 10) =>
    fetch(`${SERVER}/api/alerts/${id}/snooze?minutes=${minutes}`, {method: 'POST'}).then((r) => json<Alert>(r)),
};

export function useScreenSocket(onMessage: (msg: ScreenMessage) => void, onStatus: (up: boolean) => void) {
  const handler = useRef(onMessage);
  const status = useRef(onStatus);
  handler.current = onMessage;
  status.current = onStatus;

  useEffect(() => {
    let ws: WebSocket | null = null;
    let retry: ReturnType<typeof setTimeout> | undefined;
    let closed = false;
    const connect = () => {
      ws = new WebSocket(WS_URL);
      // Vega's WebSocket can deliver one large text message as several onmessage chunks,
      // so keep appending until the text parses as a whole JSON message.
      let partial = '';
      ws.onopen = () => status.current(true);
      ws.onmessage = (e) => {
        partial += String(e.data);
        let msg: ScreenMessage;
        try {
          msg = JSON.parse(partial);
        } catch {
          if (!partial.startsWith('{') || partial.length > 1_000_000) {
            partial = '';
          }
          return;
        }
        partial = '';
        handler.current(msg);
      };
      ws.onerror = () => ws?.close();
      ws.onclose = () => {
        status.current(false);
        if (!closed) {
          retry = setTimeout(connect, 2000);
        }
      };
    };
    connect();
    return () => {
      closed = true;
      if (retry) {
        clearTimeout(retry);
      }
      ws?.close();
    };
  }, []);
}
