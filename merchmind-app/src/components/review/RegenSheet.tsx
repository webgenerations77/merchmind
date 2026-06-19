import React, { useState, useCallback } from 'react';
import { View, Text, TextInput, Pressable, ScrollView, StyleSheet, ActivityIndicator } from 'react-native';
import BottomSheet, { BottomSheetScrollView } from '@gorhom/bottom-sheet';
import { colors, typography, spacing } from '../../theme';

const QUICK_TWEAKS = [
  'More minimal',
  'Add humor',
  'Simpler',
  'Bolder colors',
  'Remove text',
  'More detailed',
  'Different style',
];

interface Props {
  bottomSheetRef: React.RefObject<BottomSheet>;
  currentPrompt: string;
  onRegenerate: (newPrompt: string) => Promise<void>;
}

export function RegenSheet({ bottomSheetRef, currentPrompt, onRegenerate }: Props) {
  const [prompt, setPrompt] = useState(currentPrompt);
  const [isLoading, setIsLoading] = useState(false);

  const applyTweak = useCallback((tweak: string) => {
    setPrompt(prev => `${prev}. ${tweak}.`);
  }, []);

  const handleRegenerate = async () => {
    setIsLoading(true);
    try {
      await onRegenerate(prompt);
      bottomSheetRef.current?.close();
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <BottomSheet
      ref={bottomSheetRef}
      index={-1}
      snapPoints={['70%']}
      enablePanDownToClose
      backgroundStyle={{ backgroundColor: colors.bg.elevated }}
      handleIndicatorStyle={{ backgroundColor: colors.border }}
    >
      <BottomSheetScrollView contentContainerStyle={styles.container}>
        <Text style={styles.title}>Edit Prompt</Text>

        <TextInput
          value={prompt}
          onChangeText={setPrompt}
          style={styles.promptInput}
          multiline
          numberOfLines={6}
          placeholder="Describe the design..."
          placeholderTextColor={colors.text.tertiary}
          accessibilityLabel="Design prompt"
        />

        <Text style={styles.sectionLabel}>Quick tweaks</Text>
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.tweaksContent}
        >
          {QUICK_TWEAKS.map(tweak => (
            <Pressable
              key={tweak}
              style={styles.tweakChip}
              onPress={() => applyTweak(tweak)}
              accessibilityRole="button"
              accessibilityLabel={`Apply tweak: ${tweak}`}
            >
              <Text style={styles.tweakText}>{tweak}</Text>
            </Pressable>
          ))}
        </ScrollView>

        <View style={styles.actions}>
          <Pressable
            style={styles.cancelBtn}
            onPress={() => bottomSheetRef.current?.close()}
            accessibilityRole="button"
            accessibilityLabel="Cancel regeneration"
          >
            <Text style={styles.cancelText}>Cancel</Text>
          </Pressable>
          <Pressable
            style={[styles.regenBtn, isLoading && styles.disabled]}
            onPress={handleRegenerate}
            disabled={isLoading}
            accessibilityRole="button"
            accessibilityLabel="Regenerate design"
          >
            {isLoading ? (
              <ActivityIndicator color={colors.white} size="small" />
            ) : (
              <Text style={styles.regenText}>Regenerate →</Text>
            )}
          </Pressable>
        </View>
      </BottomSheetScrollView>
    </BottomSheet>
  );
}

const styles = StyleSheet.create({
  container: {
    padding: spacing.lg,
    gap: spacing.lg,
    paddingBottom: 40,
  },
  title: {
    ...typography.heading,
    color: colors.text.primary,
  },
  promptInput: {
    ...typography.body,
    color: colors.text.primary,
    backgroundColor: colors.bg.tertiary,
    borderRadius: 10,
    padding: spacing.md,
    borderWidth: 1,
    borderColor: colors.border,
    textAlignVertical: 'top',
    minHeight: 120,
  },
  sectionLabel: {
    ...typography.caption,
    color: colors.text.tertiary,
    textTransform: 'uppercase',
    letterSpacing: 1,
  },
  tweaksContent: {
    gap: spacing.sm,
    paddingRight: spacing.sm,
  },
  tweakChip: {
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: colors.action.regen,
    backgroundColor: `${colors.action.regen}22`,
    minHeight: 36,
    alignItems: 'center',
    justifyContent: 'center',
  },
  tweakText: {
    ...typography.caption,
    color: colors.action.regen,
    fontWeight: '600',
  },
  actions: {
    flexDirection: 'row',
    gap: spacing.md,
    marginTop: spacing.md,
  },
  cancelBtn: {
    flex: 1,
    minHeight: 52,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 10,
    borderWidth: 1,
    borderColor: colors.border,
  },
  cancelText: {
    ...typography.subheading,
    color: colors.text.secondary,
  },
  regenBtn: {
    flex: 2,
    minHeight: 52,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 10,
    backgroundColor: colors.action.regen,
  },
  regenText: {
    ...typography.subheading,
    color: colors.white,
  },
  disabled: { opacity: 0.5 },
});
