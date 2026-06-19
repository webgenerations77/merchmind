import React, { useMemo } from 'react';
import { View, Text, FlatList, Pressable, StyleSheet } from 'react-native';
import BottomSheet, { BottomSheetView } from '@gorhom/bottom-sheet';
import { colors, typography, spacing } from '../../theme';
import { getUpcomingMondays } from '../../utils/formatters';
import { format } from 'date-fns';

interface Props {
  bottomSheetRef: React.RefObject<BottomSheet>;
  onSelect: (week: string) => void;
}

export function DelayPicker({ bottomSheetRef, onSelect }: Props) {
  const mondays = useMemo(() => getUpcomingMondays(12), []);

  return (
    <BottomSheet
      ref={bottomSheetRef}
      index={-1}
      snapPoints={['55%']}
      enablePanDownToClose
      backgroundStyle={{ backgroundColor: colors.bg.elevated }}
      handleIndicatorStyle={{ backgroundColor: colors.border }}
    >
      <BottomSheetView style={styles.container}>
        <Text style={styles.title}>Delay to week of…</Text>
        <FlatList
          data={mondays}
          keyExtractor={item => item.label}
          renderItem={({ item }) => (
            <Pressable
              style={styles.row}
              onPress={() => {
                onSelect(format(item.date, 'yyyy-MM-dd'));
                bottomSheetRef.current?.close();
              }}
              accessibilityRole="button"
              accessibilityLabel={`Delay to ${item.label}`}
            >
              <Text style={styles.dateLabel}>{item.label}</Text>
              {item.holiday && (
                <Text style={styles.holiday}>{item.holiday}</Text>
              )}
            </Pressable>
          )}
          showsVerticalScrollIndicator={false}
        />
      </BottomSheetView>
    </BottomSheet>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: spacing.lg,
  },
  title: {
    ...typography.heading,
    color: colors.text.primary,
    marginBottom: spacing.md,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
    minHeight: 52,
  },
  dateLabel: {
    ...typography.body,
    color: colors.text.primary,
  },
  holiday: {
    ...typography.caption,
    color: colors.action.delay,
  },
});
