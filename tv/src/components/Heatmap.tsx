import React, {useState} from 'react';
import {Pressable, StyleSheet, Text, View} from 'react-native';
import {TVFocusGuideView} from '@amazon-devices/react-native-kepler';
import type {Grid, Zone} from '../api';
import {colors, hourLabel} from '../theme';

interface Props {
  grid: Grid;
  zones: Zone[];
  onOpen: (zoneId: string, hourStart: number) => void;
}

export const Heatmap = ({grid, zones, onOpen}: Props) => {
  const [focus, setFocus] = useState<[number, number] | null>(null);
  const max = Math.max(1, ...Object.values(grid.counts).flat());
  const byId = Object.fromEntries(zones.map((z) => [z.id, z]));
  const lastCol = grid.hours.length - 1;

  return (
    <View style={styles.panel}>
      <View style={styles.titleRow}>
        <Text style={styles.title}>ChronoGrid</Text>
        <Text style={styles.hint}>activity by zone × hour · arrows to move · OK to open</Text>
      </View>
      <View style={styles.row}>
        <View style={styles.labelCell} />
        {grid.hours.map((h) => (
          <Text key={h} style={styles.hour}>
            {hourLabel(h)}
          </Text>
        ))}
      </View>
      <TVFocusGuideView autoFocus>
        {grid.zones.map((zid, r) => {
          const zone = byId[zid];
          return (
            <View key={zid} style={styles.row}>
              <View style={styles.labelCell}>
                <View style={[styles.dot, zone?.presence.present && styles.dotOn]} />
                <View>
                  <Text style={styles.zoneName}>{zone?.name ?? zid}</Text>
                  <Text style={styles.zoneMeta}>{zone ? `${zone.objects.length} items` : ''}</Text>
                </View>
              </View>
              {grid.counts[zid].map((n, c) => {
                const focused = focus?.[0] === r && focus?.[1] === c;
                const level = n === 0 ? 0 : 0.18 + 0.82 * (n / max);
                return (
                  <Pressable
                    key={`${zid}-${c}`}
                    hasTVPreferredFocus={r === 0 && c === lastCol}
                    onFocus={() => setFocus([r, c])}
                    onPress={() => onOpen(zid, grid.hours[c])}
                    style={[
                      styles.cell,
                      {backgroundColor: `rgba(62, 224, 176, ${level})`},
                      focused && styles.cellFocused,
                    ]}>
                    <Text style={[styles.count, level > 0.6 && styles.countDark]}>{n > 0 ? n : ''}</Text>
                  </Pressable>
                );
              })}
            </View>
          );
        })}
      </TVFocusGuideView>
    </View>
  );
};

const styles = StyleSheet.create({
  panel: {
    flex: 1,
    backgroundColor: colors.panel,
    borderRadius: 20,
    padding: 32,
    borderWidth: 1,
    borderColor: colors.panelEdge,
  },
  titleRow: {flexDirection: 'row', alignItems: 'baseline', marginBottom: 20},
  title: {color: colors.text, fontSize: 34, fontWeight: '700', marginRight: 24},
  hint: {color: colors.muted, fontSize: 20},
  row: {flexDirection: 'row', alignItems: 'center', marginBottom: 10},
  labelCell: {width: 260, flexDirection: 'row', alignItems: 'center'},
  dot: {width: 14, height: 14, borderRadius: 7, backgroundColor: '#2b3746', marginRight: 14},
  dotOn: {backgroundColor: colors.accent},
  zoneName: {color: colors.text, fontSize: 24, fontWeight: '600'},
  zoneMeta: {color: colors.muted, fontSize: 18},
  hour: {flex: 1, color: colors.muted, fontSize: 20, textAlign: 'center'},
  cell: {
    flex: 1,
    height: 92,
    marginHorizontal: 5,
    borderRadius: 12,
    borderWidth: 3,
    borderColor: 'transparent',
    alignItems: 'center',
    justifyContent: 'center',
  },
  cellFocused: {borderColor: colors.focus, transform: [{scale: 1.08}]},
  count: {color: colors.text, fontSize: 24, fontWeight: '700'},
  countDark: {color: '#06261d'},
});
