import React, { useState } from 'react';
import { View, Text, TextInput, Pressable, ScrollView, StyleSheet } from 'react-native';
import { colors, typography, spacing } from '../../theme';

interface Props {
  title: string;
  tags: string[];
  seoDescription: string;
  onTitleChange: (title: string) => void;
  onTagsChange: (tags: string[]) => void;
  onDescriptionChange: (desc: string) => void;
}

export function ListingDetails({ title, tags, seoDescription, onTitleChange, onTagsChange, onDescriptionChange }: Props) {
  const [descExpanded, setDescExpanded] = useState(false);

  return (
    <View style={styles.container}>
      <Text style={styles.sectionLabel}>Listing</Text>

      <TextInput
        value={title}
        onChangeText={onTitleChange}
        style={styles.titleInput}
        multiline
        placeholder="Listing title"
        placeholderTextColor={colors.text.tertiary}
        accessibilityLabel="Listing title"
      />

      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        style={styles.tagsScroll}
        contentContainerStyle={styles.tagsContent}
      >
        {tags.map((tag, i) => (
          <View key={i} style={styles.tag}>
            <Text style={styles.tagText}>{tag}</Text>
          </View>
        ))}
      </ScrollView>

      <Pressable
        onPress={() => setDescExpanded(v => !v)}
        style={styles.descToggle}
        accessibilityRole="button"
        accessibilityState={{ expanded: descExpanded }}
      >
        <Text style={styles.descToggleText}>
          SEO Description {descExpanded ? '▲' : '▾'}
        </Text>
      </Pressable>

      {descExpanded && (
        <TextInput
          value={seoDescription}
          onChangeText={onDescriptionChange}
          style={styles.descInput}
          multiline
          numberOfLines={4}
          placeholder="SEO description..."
          placeholderTextColor={colors.text.tertiary}
          accessibilityLabel="SEO description"
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    padding: spacing.lg,
    gap: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  sectionLabel: {
    ...typography.caption,
    color: colors.text.tertiary,
    textTransform: 'uppercase',
    letterSpacing: 1,
  },
  titleInput: {
    ...typography.subheading,
    color: colors.text.primary,
    backgroundColor: colors.bg.tertiary,
    borderRadius: 8,
    padding: spacing.md,
    borderWidth: 1,
    borderColor: colors.border,
  },
  tagsScroll: { marginTop: spacing.xs },
  tagsContent: { gap: spacing.xs, flexDirection: 'row', paddingRight: spacing.sm },
  tag: {
    paddingHorizontal: spacing.sm,
    paddingVertical: 4,
    borderRadius: 12,
    backgroundColor: colors.bg.tertiary,
    borderWidth: 1,
    borderColor: colors.border,
  },
  tagText: {
    ...typography.caption,
    color: colors.text.secondary,
  },
  descToggle: {
    paddingVertical: spacing.xs,
    minHeight: 44,
    justifyContent: 'center',
  },
  descToggleText: {
    ...typography.caption,
    color: colors.accent,
  },
  descInput: {
    ...typography.body,
    color: colors.text.primary,
    backgroundColor: colors.bg.tertiary,
    borderRadius: 8,
    padding: spacing.md,
    borderWidth: 1,
    borderColor: colors.border,
    textAlignVertical: 'top',
  },
});
