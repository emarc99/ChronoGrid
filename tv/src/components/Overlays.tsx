import React, {useEffect, useRef} from 'react';
import {Animated, StyleSheet, Text, View} from 'react-native';
import type {Alert} from '../api';
import {colors} from '../theme';
import {FocusButton} from './FocusButton';

export const AlertCard = ({alert, onSnooze}: {alert: Alert; onSnooze: () => void}) => {
  const slide = useRef(new Animated.Value(500)).current;
  useEffect(() => {
    Animated.spring(slide, {toValue: 0, useNativeDriver: true}).start();
  }, [slide]);
  const critical = alert.severity === 'critical';
  return (
    <Animated.View style={[styles.alert, critical && styles.alertCritical, {transform: [{translateX: slide}]}]}>
      <Text style={[styles.sev, critical && styles.sevCritical]}>
        {critical ? '⛔' : '⚠'} {alert.severity.toUpperCase()} · real-world lint
      </Text>
      <Text style={styles.alertTitle}>{alert.title}</Text>
      <Text style={styles.alertBody}>{alert.body}</Text>
      {alert.evidence.slice(0, 3).map((e) => (
        <Text key={e} style={styles.evidence}>
          · {e}
        </Text>
      ))}
      <View style={styles.row}>
        <FocusButton label="Snooze 10 min" preferred onPress={onSnooze} />
      </View>
    </Animated.View>
  );
};

export interface Turn {
  user: string;
  reply?: string;
  tools: string[];
}

export const AlexaStrip = ({turn}: {turn: Turn | null}) => {
  if (!turn) {
    return (
      <View style={styles.strip}>
        <Text style={styles.muted}>Say “Alexa, where did I leave my keys?” · Alexa+ drives this screen over MCP</Text>
      </View>
    );
  }
  return (
    <View style={styles.strip}>
      <Text style={styles.user}>“{turn.user}”</Text>
      {turn.tools.length > 0 && (
        <View style={styles.row}>
          {turn.tools.map((t, i) => (
            <Text key={`${t}-${i}`} style={styles.chip}>
              mcp → {t}
            </Text>
          ))}
        </View>
      )}
      <Text style={styles.reply}>{turn.reply ?? 'Alexa is thinking…'}</Text>
    </View>
  );
};

const styles = StyleSheet.create({
  alert: {
    position: 'absolute',
    right: 48,
    top: 120,
    width: 620,
    backgroundColor: '#2a1d08',
    borderColor: colors.warn,
    borderWidth: 3,
    borderRadius: 20,
    padding: 28,
  },
  alertCritical: {backgroundColor: '#2c0e0e', borderColor: colors.danger},
  sev: {color: colors.warn, fontSize: 20, fontWeight: '700', letterSpacing: 1},
  sevCritical: {color: colors.danger},
  alertTitle: {color: colors.text, fontSize: 32, fontWeight: '700', marginTop: 8},
  alertBody: {color: colors.text, fontSize: 24, lineHeight: 34, marginTop: 8},
  evidence: {color: colors.muted, fontSize: 20, marginTop: 4},
  row: {flexDirection: 'row', flexWrap: 'wrap', marginTop: 16},
  strip: {
    marginTop: 20,
    backgroundColor: colors.panel,
    borderRadius: 16,
    paddingHorizontal: 28,
    paddingVertical: 18,
    borderWidth: 1,
    borderColor: colors.panelEdge,
    minHeight: 110,
  },
  muted: {color: colors.muted, fontSize: 22},
  user: {color: colors.muted, fontSize: 22, fontStyle: 'italic'},
  reply: {color: colors.text, fontSize: 26, marginTop: 8},
  chip: {
    color: colors.accent,
    fontSize: 18,
    borderWidth: 1,
    borderColor: '#1f5a49',
    borderRadius: 8,
    paddingHorizontal: 10,
    paddingVertical: 4,
    marginRight: 10,
    marginTop: -6,
  },
});
