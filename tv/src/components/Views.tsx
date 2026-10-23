import React, {useCallback, useEffect, useRef, useState} from 'react';
import {Animated, StyleSheet, Text, View} from 'react-native';
import type {LedgerEvent, Rule, Zone} from '../api';
import {clock, colors, mono} from '../theme';
import {ClipPlayer} from './ClipPlayer';
import {FocusButton} from './FocusButton';

const FRAME_W = 880;
const FRAME_H = 495;

function bounds(poly: [number, number][]) {
  const xs = poly.map((p) => p[0]);
  const ys = poly.map((p) => p[1]);
  return {x: Math.min(...xs), y: Math.min(...ys), w: Math.max(...xs) - Math.min(...xs), h: Math.max(...ys) - Math.min(...ys)};
}

type Area = {left: number; top: number; width: number; height: number};
const FULL_FRAME: Area = {left: 0, top: 0, width: FRAME_W, height: FRAME_H};

/** Where a video of this size lands inside the frame when scaled to fit (letterboxed). */
function fitted(width: number, height: number): Area {
  const scale = Math.min(FRAME_W / width, FRAME_H / height);
  const w = width * scale;
  const h = height * scale;
  return {left: (FRAME_W - w) / 2, top: (FRAME_H - h) / 2, width: w, height: h};
}

// Webcams record 4:3; the Vega Virtual Device doesn't always report the decoded size.
const DEFAULT_CLIP = fitted(4, 3);

function Pulse({bbox, label, area}: {bbox: [number, number, number, number]; label: string; area: Area}) {
  const glow = useRef(new Animated.Value(0.35)).current;
  useEffect(() => {
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(glow, {toValue: 1, duration: 700, useNativeDriver: true}),
        Animated.timing(glow, {toValue: 0.35, duration: 700, useNativeDriver: true}),
      ]),
    );
    loop.start();
    return () => loop.stop();
  }, [glow]);
  const [x1, y1, x2, y2] = bbox;
  return (
    <Animated.View
      style={[
        styles.bbox,
        {
          left: area.left + x1 * area.width,
          top: area.top + y1 * area.height,
          width: (x2 - x1) * area.width,
          height: (y2 - y1) * area.height,
          opacity: glow,
        },
      ]}>
      <Text style={styles.bboxLabel}>{label}</Text>
    </Animated.View>
  );
}

/** Rewind: the 5-second placement clip when there is one, otherwise the camera's zone map. */
export const RewindView = ({data, zones}: {data: any; zones: Zone[]}) => {
  const history: any[] = data.history ?? [];
  const [clipFailed, setClipFailed] = useState(false);
  const [videoArea, setVideoArea] = useState<Area | null>(null);
  const onClipError = useCallback(() => setClipFailed(true), []);
  const onClipSize = useCallback((w: number, h: number) => setVideoArea(fitted(w, h)), []);
  useEffect(() => {
    setClipFailed(false);
    setVideoArea(null);
  }, [data.clip_url]);
  const playing = Boolean(data.clip_url) && !clipFailed;
  return (
    <View style={styles.panel}>
      <Text style={styles.title}>
        git log · <Text style={styles.accent}>{data.object ?? data.label}</Text>
      </Text>
      <View style={styles.split}>
        <View style={[styles.frame, playing && styles.frameVideo]}>
          {playing && <ClipPlayer url={data.clip_url} onError={onClipError} onSize={onClipSize} />}
          {!playing && zones.map((z) => {
            const b = bounds(z.polygon);
            const hit = z.id === data.zone_id;
            return (
              <View
                key={z.id}
                style={[
                  styles.zone,
                  {left: b.x * FRAME_W, top: b.y * FRAME_H, width: b.w * FRAME_W, height: b.h * FRAME_H},
                  hit && styles.zoneHit,
                ]}>
                <Text style={[styles.zoneName, hit && styles.accent]}>{z.name}</Text>
              </View>
            );
          })}
          {data.bbox && (
            <Pulse bbox={data.bbox} label={data.object ?? ''} area={playing ? videoArea ?? DEFAULT_CLIP : FULL_FRAME} />
          )}
          <Text style={styles.stamp}>{data.ts ? `${clock(data.ts)} · camera 1` : 'camera 1'}</Text>
        </View>
        <View style={styles.side}>
          <Text style={styles.say}>{data.say}</Text>
          <Text style={styles.h4}>History</Text>
          {history.slice(0, 5).map((h) => (
            <View key={h.event_id} style={styles.histRow}>
              <Text style={styles.histTime}>{h.time_text}</Text>
              <Text style={styles.histText}>
                {h.kind} · {h.zone_name}
              </Text>
            </View>
          ))}
          <Text style={styles.muted}>
            {playing ? 'Looping the 5-second clip · ' : ''}saved privately in S3 · faces blurred on-device
          </Text>
        </View>
      </View>
    </View>
  );
};

export const CellView = ({zoneName, hour, events}: {zoneName: string; hour: number; events: LedgerEvent[]}) => (
  <View style={styles.panel}>
    <Text style={styles.title}>
      {zoneName} · {clock(hour)} – {clock(hour + 3600)}
    </Text>
    <View style={styles.code}>
      {events.length === 0 && <Text style={styles.same}># nothing happened here</Text>}
      {events.map((e) => (
        <Text key={e.id} style={e.kind === 'removed' ? styles.del : styles.add}>
          {e.kind === 'removed' ? '-' : '+'} {clock(e.ts)} {e.kind} {e.label}
        </Text>
      ))}
    </View>
    <Text style={styles.muted}>Ask Alexa “where is the …” to rewind any of these.</Text>
  </View>
);

export const DiffView = ({data}: {data: any}) => {
  const base = data.base;
  return (
    <View style={styles.panel}>
      <Text style={styles.title}>git diff · {data.zone_name}</Text>
      <Text style={styles.muted}>
        {base ? `vs ${base.kind === 'commit' ? `commit #${base.id} "${base.message}"` : 'earlier'} at ${clock(base.ts)}` : 'no commit yet'}
      </Text>
      <View style={styles.code}>
        <Text style={styles.meta}>
          diff --chrono a/{data.zone_id}@{base ? clock(base.ts) : '-'} b/{data.zone_id}@now
        </Text>
        {data.removed?.map((r: any) => (
          <Text key={`-${r.label}`} style={styles.del}>
            - {r.label}
            <Text style={styles.note}>{r.now_in_name ? `   # now in ${r.now_in_name}` : '   # not seen since'}</Text>
          </Text>
        ))}
        {data.added?.map((a: string) => (
          <Text key={`+${a}`} style={styles.add}>
            + {a}
          </Text>
        ))}
        {data.unchanged?.map((u: string) => (
          <Text key={` ${u}`} style={styles.same}>
            {'  '}
            {u}
          </Text>
        ))}
        {!data.removed?.length && !data.added?.length && <Text style={styles.same}>  # working tree clean</Text>}
      </View>
      <Text style={styles.say}>{data.say}</Text>
    </View>
  );
};

export const StatusView = ({data}: {data: any}) => (
  <View style={styles.panel}>
    <Text style={styles.title}>git status</Text>
    <View style={styles.cards}>
      {data.zones?.map((z: any) => (
        <View key={z.zone_id} style={[styles.card, z.uncommitted && styles.cardDirty]}>
          <Text style={styles.cardHead}>
            {z.person_present ? '● ' : '○ '}
            {z.zone_name}
            {z.uncommitted ? '  · modified' : ''}
          </Text>
          {z.objects.length ? (
            z.objects.map((o: string) => (
              <Text key={o} style={styles.cardItem}>
                {o}
              </Text>
            ))
          ) : (
            <Text style={styles.muted}>empty</Text>
          )}
        </View>
      ))}
    </View>
    {data.appliances_on?.map((a: any) => (
      <Text key={a.label} style={styles.warnText}>
        ⚠ {a.label} on since {a.on_since}
      </Text>
    ))}
  </View>
);

export const CommitView = ({data}: {data: any}) => (
  <View style={styles.panel}>
    <Text style={styles.title}>git commit · {data.zone_name}</Text>
    <View style={styles.code}>
      <Text style={styles.meta}>
        [main #{data.id}] {data.message}
      </Text>
      <Text style={styles.same}>
        {' '}
        {data.objects?.length ?? 0} objects tracked at {data.ts ? clock(data.ts) : ''}
      </Text>
      {data.objects?.map((o: string) => (
        <Text key={o} style={styles.add}>
          + {o}
        </Text>
      ))}
    </View>
    <Text style={styles.say}>{data.say}</Text>
  </View>
);

function describe(c: Record<string, any>): string {
  switch (c.type) {
    case 'appliance_on':
      return `${c.appliance} is on${c.for_seconds ? ` for ${c.for_seconds}s` : ''}`;
    case 'person_absent':
      return `nobody at ${c.zone} for ${c.for_seconds}s`;
    case 'object_missing':
      return `${c.object} is not in ${c.zone}`;
    case 'object_present':
      return `${c.object} is in ${c.zone}`;
    case 'time_window':
      return `time is between ${c.start} and ${c.end}`;
    default:
      return c.type;
  }
}

export const RulePR = ({rule, onAction}: {rule: Rule; onAction: (a: 'approve' | 'reject') => void}) => (
  <View style={styles.panel}>
    <Text style={styles.title}>
      Lint rule PR #{rule.id} · {rule.spec.name}
      <Text style={rule.status === 'active' ? styles.accent : styles.warnText}>  {rule.status}</Text>
    </Text>
    {rule.source_text && <Text style={styles.quote}>“{rule.source_text}”</Text>}
    <Text style={styles.h4}>Fires when all of these hold</Text>
    {rule.spec.when.map((c, i) => (
      <Text key={i} style={styles.cond}>
        • {describe(c)}
      </Text>
    ))}
    <Text style={styles.h4}>Then say</Text>
    <Text style={styles.say}>{rule.spec.message}</Text>
    <Text style={styles.muted}>
      severity {rule.spec.severity} · compiled by Amazon Bedrock, enforced deterministically
    </Text>
    {rule.status === 'proposed' && (
      <View style={styles.actions}>
        <FocusButton label="Approve & enforce" primary preferred onPress={() => onAction('approve')} />
        <FocusButton label="Reject" onPress={() => onAction('reject')} />
      </View>
    )}
  </View>
);

const styles = StyleSheet.create({
  panel: {
    flex: 1,
    backgroundColor: colors.panel,
    borderRadius: 20,
    padding: 32,
    borderWidth: 1,
    borderColor: colors.panelEdge,
  },
  title: {color: colors.text, fontSize: 34, fontWeight: '700', marginBottom: 12},
  accent: {color: colors.accent},
  muted: {color: colors.muted, fontSize: 20, marginTop: 12},
  say: {color: colors.text, fontSize: 26, lineHeight: 36, marginTop: 16},
  h4: {color: colors.muted, fontSize: 20, marginTop: 20, marginBottom: 6, textTransform: 'uppercase', letterSpacing: 1},
  split: {flexDirection: 'row', marginTop: 8},
  frame: {
    width: FRAME_W,
    height: FRAME_H,
    backgroundColor: '#070a0e',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.panelEdge,
    overflow: 'hidden',
  },
  frameVideo: {backgroundColor: '#000'},
  zone: {position: 'absolute', borderWidth: 2, borderColor: '#2b3746', borderRadius: 8, padding: 8},
  zoneHit: {borderColor: colors.accent, backgroundColor: 'rgba(62,224,176,0.08)'},
  zoneName: {color: colors.muted, fontSize: 18},
  bbox: {position: 'absolute', borderWidth: 4, borderColor: colors.accent, borderRadius: 6},
  bboxLabel: {
    position: 'absolute',
    top: -30,
    left: -4,
    backgroundColor: colors.accent,
    color: '#06261d',
    fontSize: 18,
    fontWeight: '700',
    paddingHorizontal: 8,
  },
  stamp: {position: 'absolute', right: 12, bottom: 8, color: colors.muted, fontSize: 16, fontFamily: mono},
  side: {flex: 1, marginLeft: 32},
  histRow: {flexDirection: 'row', marginBottom: 6},
  histTime: {color: colors.accent, fontSize: 22, width: 130, fontFamily: mono},
  histText: {color: colors.text, fontSize: 22},
  code: {backgroundColor: '#070a0e', borderRadius: 12, padding: 24, marginTop: 16},
  meta: {color: colors.muted, fontSize: 22, fontFamily: mono, marginBottom: 8},
  add: {color: colors.add, fontSize: 26, fontFamily: mono, lineHeight: 38},
  del: {color: colors.del, fontSize: 26, fontFamily: mono, lineHeight: 38},
  same: {color: colors.muted, fontSize: 26, fontFamily: mono, lineHeight: 38},
  note: {color: colors.muted, fontSize: 22},
  cards: {flexDirection: 'row', flexWrap: 'wrap', marginTop: 8},
  card: {
    width: 380,
    backgroundColor: '#0e141c',
    borderRadius: 14,
    padding: 20,
    marginRight: 20,
    marginBottom: 20,
    borderWidth: 2,
    borderColor: colors.panelEdge,
  },
  cardDirty: {borderColor: colors.warn},
  cardHead: {color: colors.text, fontSize: 24, fontWeight: '700', marginBottom: 8},
  cardItem: {color: colors.text, fontSize: 22, lineHeight: 32},
  warnText: {color: colors.warn, fontSize: 24, marginTop: 8},
  quote: {color: colors.text, fontSize: 26, fontStyle: 'italic', marginVertical: 8},
  cond: {color: colors.text, fontSize: 24, lineHeight: 36},
  actions: {flexDirection: 'row', marginTop: 28},
});
