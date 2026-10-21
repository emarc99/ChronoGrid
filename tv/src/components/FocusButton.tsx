import React, {useState} from 'react';
import {Pressable, StyleSheet, Text, ViewStyle} from 'react-native';
import {colors} from '../theme';

interface Props {
  label: string;
  onPress: () => void;
  primary?: boolean;
  preferred?: boolean;
  style?: ViewStyle;
}

export const FocusButton = ({label, onPress, primary, preferred, style}: Props) => {
  const [focused, setFocused] = useState(false);
  return (
    <Pressable
      onPress={onPress}
      onFocus={() => setFocused(true)}
      onBlur={() => setFocused(false)}
      hasTVPreferredFocus={preferred}
      accessibilityRole="button"
      accessibilityLabel={label}
      style={[styles.button, primary && styles.primary, focused && styles.focused, style]}>
      <Text style={[styles.label, primary && styles.primaryLabel]}>{label}</Text>
    </Pressable>
  );
};

const styles = StyleSheet.create({
  button: {
    paddingHorizontal: 28,
    paddingVertical: 14,
    borderRadius: 12,
    borderWidth: 3,
    borderColor: colors.panelEdge,
    backgroundColor: colors.panel,
    marginRight: 20,
  },
  primary: {backgroundColor: '#13352c', borderColor: '#1f5a49'},
  focused: {borderColor: colors.focus, transform: [{scale: 1.06}]},
  label: {color: colors.text, fontSize: 24, fontWeight: '600'},
  primaryLabel: {color: colors.accent},
});
