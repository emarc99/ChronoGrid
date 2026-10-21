import React, {useCallback, useEffect, useRef, useState} from 'react';
import {BackHandler, StyleSheet, Text, View, useWindowDimensions} from 'react-native';
import {api, useScreenSocket} from './api';
import type {Alert, Grid, LedgerEvent, Rule, ScreenMessage, ScreenView, State} from './api';
import {Heatmap} from './components/Heatmap';
import {AlertCard, AlexaStrip, Turn} from './components/Overlays';
import {CellView, CommitView, DiffView, RewindView, RulePR, StatusView} from './components/Views';
import {clock, colors, setUtcOffset} from './theme';

// Layout is authored for a 1920x1080 canvas and scaled to the device's logical size.
const DESIGN_W = 1920;
const DESIGN_H = 1080;

type Screen =
  | {kind: 'home'}
  | {kind: 'cell'; zoneName: string; hour: number; events: LedgerEvent[]}
  | {kind: 'view'; view: ScreenView; data: any}
  | {kind: 'rule'; rule: Rule};

const IDLE_MS = 60_000;

export const App = () => {
  const [state, setState] = useState<State | null>(null);
  const [grid, setGrid] = useState<Grid | null>(null);
  const [screen, setScreen] = useState<Screen>({kind: 'home'});
  const [alert, setAlert] = useState<Alert | null>(null);
  const [turn, setTurn] = useState<Turn | null>(null);
  const [online, setOnline] = useState(false);
  const [now, setNow] = useState(Date.now() / 1000);
  const idle = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const win = useWindowDimensions();
  const k = Math.min(win.width / DESIGN_W, win.height / DESIGN_H);

  const refresh = useCallback(() => {
    api
      .state()
      .then((s) => {
        setUtcOffset(s.utc_offset ?? 0);
        setState(s);
      })
      .catch(() => undefined);
    api.grid(8).then(setGrid).catch(() => undefined);
  }, []);

  const show = useCallback((next: Screen) => {
    setScreen(next);
    if (idle.current) {
      clearTimeout(idle.current);
    }
    if (next.kind !== 'home') {
      idle.current = setTimeout(() => setScreen({kind: 'home'}), IDLE_MS);
    }
  }, []);

  useEffect(() => {
    refresh();
    const tick = setInterval(() => setNow(Date.now() / 1000), 15_000);
    return () => clearInterval(tick);
  }, [refresh]);

  useEffect(() => {
    const sub = BackHandler.addEventListener('hardwareBackPress', () => {
      if (screen.kind === 'home') {
        return false;
      }
      show({kind: 'home'});
      return true;
    });
    return () => sub.remove();
  }, [screen.kind, show]);

  const onMessage = useCallback(
    (msg: ScreenMessage) => {
      switch (msg.type) {
        case 'screen':
          if (msg.view === 'rule_pr') {
            show({kind: 'rule', rule: msg.data});
          } else {
            show({kind: 'view', view: msg.view, data: msg.data});
          }
          break;
        case 'rule_updated':
          setScreen((s) => (s.kind === 'rule' && s.rule.id === msg.rule.id ? {kind: 'rule', rule: msg.rule} : s));
          refresh();
          break;
        case 'alert':
          setAlert(msg.alert);
          break;
        case 'alert_resolved':
        case 'alert_snoozed':
          setAlert((a) => (a && a.id === msg.alert.id ? null : a));
          break;
        case 'utterance':
          setTurn({user: msg.text, tools: []});
          break;
        case 'assistant':
          setTurn({user: msg.text, reply: msg.reply, tools: msg.tools.map((t) => t.tool)});
          break;
        case 'event':
        case 'appliance':
          refresh();
          break;
      }
    },
    [refresh, show],
  );

  useScreenSocket(onMessage, (up) => {
    setOnline(up);
    if (up) {
      refresh();
    }
  });

  useEffect(() => {
    const open = state?.alerts.find((a) => a.status === 'open');
    if (open) {
      setAlert((a) => a ?? open);
    }
  }, [state]);

  const zones = state?.zones ?? [];

  const openCell = (zoneId: string, hour: number) => {
    const zoneName = zones.find((z) => z.id === zoneId)?.name ?? zoneId;
    api
      .events(zoneId, hour, hour + 3600)
      .then((events) => show({kind: 'cell', zoneName, hour, events}))
      .catch(() => undefined);
  };

  let body: React.ReactNode;
  if (screen.kind === 'cell') {
    body = <CellView zoneName={screen.zoneName} hour={screen.hour} events={screen.events} />;
  } else if (screen.kind === 'rule') {
    body = (
      <RulePR
        rule={screen.rule}
        onAction={(a) =>
          api
            .ruleAction(screen.rule.id, a)
            .then((rule) => setScreen({kind: 'rule', rule}))
            .catch(() => undefined)
        }
      />
    );
  } else if (screen.kind === 'view') {
    const v = screen.view;
    body =
      v === 'rewind' || v === 'log' ? (
        <RewindView data={screen.data} zones={zones} />
      ) : v === 'diff' ? (
        <DiffView data={screen.data} />
      ) : v === 'commit' ? (
        <CommitView data={screen.data} />
      ) : (
        <StatusView data={screen.data} />
      );
  } else if (grid) {
    body = <Heatmap grid={grid} zones={zones} onOpen={openCell} />;
  } else {
    body = (
      <View style={styles.empty}>
        <Text style={styles.emptyText}>{online ? 'Loading the ChronoGrid…' : 'Connecting to ChronoGrid…'}</Text>
      </View>
    );
  }

  return (
    <View style={styles.screen}>
      <View
        style={[
          styles.root,
          {left: (win.width - DESIGN_W) / 2, top: (win.height - DESIGN_H) / 2, transform: [{scale: k}]},
        ]}>
        <View style={styles.header}>
          <Text style={styles.brand}>
            Chrono<Text style={styles.brandAccent}>Grid</Text>
            <Text style={styles.sub}>   git for the physical world</Text>
          </Text>
          <View style={styles.headerRight}>
            <View style={[styles.dot, online && styles.dotOn]} />
            <Text style={styles.sub}>{online ? 'live' : 'offline'}</Text>
            <Text style={styles.clock}>{clock(now)}</Text>
          </View>
        </View>
        <View style={styles.body}>{body}</View>
        <AlexaStrip turn={turn} />
        {alert && (
          <AlertCard
            key={alert.id}
            alert={alert}
            onSnooze={() => {
              api.snooze(alert.id).catch(() => undefined);
              setAlert(null);
            }}
          />
        )}
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  screen: {flex: 1, backgroundColor: colors.bg, overflow: 'hidden'},
  root: {
    position: 'absolute',
    width: DESIGN_W,
    height: DESIGN_H,
    backgroundColor: colors.bg,
    paddingHorizontal: 56,
    paddingVertical: 36,
  },
  header: {flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20},
  brand: {color: colors.text, fontSize: 40, fontWeight: '800'},
  brandAccent: {color: colors.accent},
  sub: {color: colors.muted, fontSize: 22, fontWeight: '400'},
  headerRight: {flexDirection: 'row', alignItems: 'center'},
  dot: {width: 14, height: 14, borderRadius: 7, backgroundColor: colors.danger, marginRight: 10},
  dotOn: {backgroundColor: colors.accent},
  clock: {color: colors.text, fontSize: 30, fontWeight: '600', marginLeft: 28},
  body: {flex: 1},
  empty: {flex: 1, alignItems: 'center', justifyContent: 'center'},
  emptyText: {color: colors.muted, fontSize: 30},
});
