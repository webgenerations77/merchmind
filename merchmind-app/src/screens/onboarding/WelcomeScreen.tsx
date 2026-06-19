import React from 'react';
import { View, Text, Pressable, StyleSheet, StatusBar } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { colors, typography, spacing } from '../../theme';
import type { OnboardingWelcomeProps } from '../../navigation/types';

export default function WelcomeScreen({ navigation }: OnboardingWelcomeProps) {
  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor={colors.bg.primary} />
      <View style={styles.content}>
        <View style={styles.logoSection}>
          <Text style={styles.logo}>✦ MerchMind</Text>
          <Text style={styles.tagline}>Your automated merch business.</Text>
          <Text style={styles.subtitle}>
            Wake up Monday to products ready to sell.
          </Text>
        </View>

        <View style={styles.setupBadge}>
          <Text style={styles.setupText}>⏱ Setup takes about 8 minutes</Text>
        </View>
      </View>

      <View style={styles.footer}>
        <Pressable
          style={({ pressed }) => [styles.ctaButton, pressed && styles.ctaPressed]}
          onPress={() => navigation.navigate('ConnectTools')}
          accessibilityRole="button"
          accessibilityLabel="Get started"
        >
          <Text style={styles.ctaText}>Let's go →</Text>
        </Pressable>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.bg.primary,
  },
  content: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: spacing.xxl,
    gap: spacing.xxl,
  },
  logoSection: {
    alignItems: 'center',
    gap: spacing.lg,
  },
  logo: {
    fontSize: 36,
    fontWeight: '800',
    color: colors.text.primary,
    letterSpacing: 1,
  },
  tagline: {
    ...typography.display,
    color: colors.text.primary,
    textAlign: 'center',
  },
  subtitle: {
    ...typography.body,
    color: colors.text.secondary,
    textAlign: 'center',
    lineHeight: 24,
  },
  setupBadge: {
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.bg.secondary,
  },
  setupText: {
    ...typography.caption,
    color: colors.text.secondary,
  },
  footer: {
    padding: spacing.xxl,
  },
  ctaButton: {
    backgroundColor: colors.accent,
    paddingVertical: spacing.lg,
    borderRadius: 14,
    alignItems: 'center',
    minHeight: 56,
    justifyContent: 'center',
  },
  ctaPressed: { opacity: 0.85 },
  ctaText: {
    ...typography.subheading,
    color: colors.white,
    fontSize: 18,
  },
});
