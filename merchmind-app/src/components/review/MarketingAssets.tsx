import React, { useState } from 'react';
import { View, Text, Pressable, TextInput, ScrollView, StyleSheet } from 'react-native';
import { colors, typography, spacing } from '../../theme';
import type { MarketingAsset } from '../../types/api';

interface Props {
  assets: MarketingAsset[];
  onDisable: (assetId: string) => void;
  onEdit: (assetId: string, updates: Partial<MarketingAsset>) => void;
}

export function MarketingAssets({ assets, onDisable, onEdit }: Props) {
  const [expanded, setExpanded] = useState(false);

  const channels = ['instagram', 'tiktok', 'pinterest', 'email', 'blog'];
  const channelEmojis: Record<string, string> = {
    instagram: '📸',
    tiktok: '🎵',
    pinterest: '📌',
    email: '📧',
    blog: '📝',
  };

  return (
    <View style={styles.container}>
      <Pressable
        onPress={() => setExpanded(v => !v)}
        style={styles.header}
        accessibilityRole="button"
        accessibilityState={{ expanded }}
      >
        <Text style={styles.headerText}>📣 Marketing {expanded ? '▲' : '▾'}</Text>
      </Pressable>

      {expanded && (
        <View style={styles.body}>
          {channels.map(channel => {
            const asset = assets.find(a => a.channel === channel);
            if (!asset) return null;

            return (
              <ChannelSection
                key={channel}
                emoji={channelEmojis[channel] ?? '📄'}
                channel={channel}
                asset={asset}
                onDisable={() => onDisable(asset.id)}
                onEdit={updates => onEdit(asset.id, updates)}
              />
            );
          })}
        </View>
      )}
    </View>
  );
}

interface ChannelSectionProps {
  emoji: string;
  channel: string;
  asset: MarketingAsset;
  onDisable: () => void;
  onEdit: (updates: Partial<MarketingAsset>) => void;
}

function ChannelSection({ emoji, channel, asset, onDisable, onEdit }: ChannelSectionProps) {
  const [scriptExpanded, setScriptExpanded] = useState(false);
  const channelLabel = channel.charAt(0).toUpperCase() + channel.slice(1);

  return (
    <View style={styles.channelSection}>
      <View style={styles.channelHeader}>
        <Text style={styles.channelTitle}>{emoji} {channelLabel}</Text>
        <Pressable
          onPress={onDisable}
          hitSlop={8}
          style={styles.disableBtn}
          accessibilityLabel={`Disable ${channelLabel} asset`}
        >
          <Text style={styles.disableText}>Disable</Text>
        </Pressable>
      </View>

      {channel === 'instagram' && asset.caption && (
        <Text style={styles.preview} numberOfLines={2}>{asset.caption}</Text>
      )}

      {channel === 'tiktok' && asset.hook_text && (
        <>
          <Text style={styles.hookText}>{asset.hook_text}</Text>
          {asset.full_script && (
            <Pressable onPress={() => setScriptExpanded(v => !v)} hitSlop={8}>
              <Text style={styles.expandLink}>View full script {scriptExpanded ? '▲' : '▾'}</Text>
            </Pressable>
          )}
          {scriptExpanded && asset.full_script && (
            <Text style={styles.preview}>{asset.full_script}</Text>
          )}
        </>
      )}

      {channel === 'pinterest' && asset.pin_title && (
        <Text style={styles.preview}>{asset.pin_title}</Text>
      )}

      {channel === 'email' && asset.subject_lines && (
        <View style={styles.subjectLines}>
          {asset.subject_lines.map((s, i) => (
            <View key={i} style={styles.subjectLine}>
              <View style={[styles.radio, i === 0 && styles.radioSelected]} />
              <Text style={styles.subjectText}>{s}</Text>
            </View>
          ))}
        </View>
      )}

      {channel === 'blog' && asset.blog_title && (
        <>
          <Text style={styles.preview}>{asset.blog_title}</Text>
          {asset.blog_intro && (
            <Text style={styles.preview} numberOfLines={2}>{asset.blog_intro}</Text>
          )}
        </>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  header: {
    padding: spacing.lg,
    minHeight: 44,
    justifyContent: 'center',
  },
  headerText: {
    ...typography.subheading,
    color: colors.text.primary,
  },
  body: {
    paddingHorizontal: spacing.lg,
    paddingBottom: spacing.lg,
    gap: spacing.xl,
  },
  channelSection: {
    gap: spacing.sm,
    paddingBottom: spacing.lg,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  channelHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  channelTitle: {
    ...typography.subheading,
    color: colors.text.primary,
  },
  disableBtn: {
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.xs,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: colors.border,
    minHeight: 32,
    alignItems: 'center',
    justifyContent: 'center',
  },
  disableText: {
    ...typography.caption,
    color: colors.text.secondary,
  },
  preview: {
    ...typography.body,
    color: colors.text.secondary,
    lineHeight: 20,
  },
  hookText: {
    ...typography.subheading,
    color: colors.text.primary,
  },
  expandLink: {
    ...typography.caption,
    color: colors.accent,
    marginTop: spacing.xs,
  },
  subjectLines: {
    gap: spacing.sm,
  },
  subjectLine: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: spacing.sm,
  },
  radio: {
    width: 16,
    height: 16,
    borderRadius: 8,
    borderWidth: 2,
    borderColor: colors.border,
    marginTop: 3,
  },
  radioSelected: {
    borderColor: colors.accent,
    backgroundColor: colors.accent,
  },
  subjectText: {
    ...typography.body,
    color: colors.text.secondary,
    flex: 1,
  },
});
