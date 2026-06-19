import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  Pressable,
  TextInput,
  ScrollView,
  StyleSheet,
  ActivityIndicator,
  Linking,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import BottomSheet, { BottomSheetView, BottomSheetTextInput } from '@gorhom/bottom-sheet';
import { colors, typography, spacing } from '../../theme';
import { useApiKey } from '../../hooks/useApiKey';
import { InfoCollapsible } from '../../components/shared/InfoCollapsible';
import { storage } from '../../navigation/RootNavigator';
import type { OnboardingConnectToolsProps } from '../../navigation/types';

interface ServiceConfig {
  id: string;
  name: string;
  emoji: string;
  description: string;
  placeholder: string;
  helpText: string;
}

const SERVICES: ServiceConfig[] = [
  {
    id: 'anthropic',
    name: 'Anthropic (Claude)',
    emoji: '🤖',
    description: 'Scores trends, writes copy, and makes creative decisions.',
    placeholder: 'sk-ant-...',
    helpText: 'Go to console.anthropic.com → API Keys → Create Key',
  },
  {
    id: 'openai',
    name: 'OpenAI (DALL-E 3)',
    emoji: '🎨',
    description: 'Generates text-based design images.',
    placeholder: 'sk-...',
    helpText: 'Go to platform.openai.com → API Keys → Create new secret key',
  },
  {
    id: 'replicate',
    name: 'Replicate (Stable Diffusion)',
    emoji: '🖼️',
    description: 'Primary image generation engine for illustrations.',
    placeholder: 'r8_...',
    helpText: 'Go to replicate.com → Account → API Tokens',
  },
  {
    id: 'printify',
    name: 'Printify',
    emoji: '🖨️',
    description: 'Fulfillment — creates and manages print-on-demand products.',
    placeholder: 'Enter Printify API key',
    helpText: 'Go to printify.com → My Profile → Connections → API',
  },
  {
    id: 'shopify',
    name: 'Shopify',
    emoji: '🛒',
    description: 'Your storefront — products publish here automatically.',
    placeholder: 'shpat_...',
    helpText: 'Go to your Shopify Admin → Apps → Develop Apps → Create token',
  },
];

export default function ConnectToolsScreen({ navigation }: OnboardingConnectToolsProps) {
  const [connected, setConnected] = useState<Record<string, boolean>>({});
  const [activeService, setActiveService] = useState<ServiceConfig | null>(null);
  const [keyInput, setKeyInput] = useState('');
  const bottomSheetRef = useRef<BottomSheet>(null);
  const { isValidating, result, validate, reset } = useApiKey();

  const connectedCount = Object.values(connected).filter(Boolean).length;
  const allConnected = connectedCount === SERVICES.length;

  const openSheet = (service: ServiceConfig) => {
    setActiveService(service);
    setKeyInput('');
    reset();
    bottomSheetRef.current?.expand();
  };

  const handleTest = async () => {
    if (!activeService || !keyInput.trim()) return;
    const res = await validate(activeService.id, keyInput.trim());
    if (res.valid) {
      setConnected(prev => ({ ...prev, [activeService.id]: true }));
      storage.set(`api_key_${activeService.id}`, keyInput.trim());
    }
  };

  const handleContinue = () => {
    storage.set('connected_services', JSON.stringify(Object.keys(connected)));
    navigation.navigate('PickNiches');
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
        <Text style={styles.title}>Connect your tools</Text>
        <Text style={styles.subtitle}>All 5 are required to run the pipeline</Text>

        <View style={styles.progressBar}>
          <View style={[styles.progressFill, { width: `${(connectedCount / SERVICES.length) * 100}%` }]} />
        </View>
        <Text style={styles.progressText}>{connectedCount} of {SERVICES.length} connected</Text>

        <View style={styles.list}>
          {SERVICES.map(service => {
            const isConnected = connected[service.id];
            return (
              <Pressable
                key={service.id}
                style={styles.serviceRow}
                onPress={() => openSheet(service)}
                accessibilityRole="button"
                accessibilityLabel={`Connect ${service.name}`}
              >
                <Text style={styles.emoji}>{service.emoji}</Text>
                <View style={styles.serviceInfo}>
                  <Text style={styles.serviceName}>{service.name}</Text>
                  <Text style={styles.serviceStatus}>
                    {isConnected ? '✅ Connected' : 'Tap to connect'}
                  </Text>
                </View>
                <Text style={styles.chevron}>›</Text>
              </Pressable>
            );
          })}
        </View>

        <Pressable
          style={[styles.continueBtn, !allConnected && styles.continueBtnDisabled]}
          onPress={handleContinue}
          disabled={!allConnected}
          accessibilityRole="button"
          accessibilityLabel="Continue to next step"
        >
          <Text style={styles.continueBtnText}>Continue →</Text>
        </Pressable>
      </ScrollView>

      <BottomSheet
        ref={bottomSheetRef}
        index={-1}
        snapPoints={['75%']}
        enablePanDownToClose
        backgroundStyle={{ backgroundColor: colors.bg.elevated }}
        handleIndicatorStyle={{ backgroundColor: colors.border }}
        keyboardBehavior="extend"
      >
        <BottomSheetView style={styles.sheet}>
          {activeService && (
            <>
              <Text style={styles.sheetTitle}>{activeService.emoji} {activeService.name}</Text>
              <Text style={styles.sheetHelp}>{activeService.helpText}</Text>

              <BottomSheetTextInput
                value={keyInput}
                onChangeText={setKeyInput}
                style={styles.keyInput}
                placeholder={activeService.placeholder}
                placeholderTextColor={colors.text.tertiary}
                autoCapitalize="none"
                autoCorrect={false}
                secureTextEntry
                accessibilityLabel={`${activeService.name} API key`}
              />

              {result && (
                <View style={[styles.resultBanner, { backgroundColor: result.valid ? `${colors.confidence.high}22` : `${colors.confidence.low}22` }]}>
                  <Text style={{ color: result.valid ? colors.confidence.high : colors.confidence.low }}>
                    {result.valid ? '✅ Connected successfully!' : `❌ ${result.error ?? 'Connection failed'}`}
                  </Text>
                </View>
              )}

              <Pressable
                style={[styles.testBtn, isValidating && styles.disabled]}
                onPress={handleTest}
                disabled={isValidating || !keyInput.trim()}
                accessibilityRole="button"
                accessibilityLabel="Test connection"
              >
                {isValidating ? (
                  <ActivityIndicator color={colors.white} />
                ) : (
                  <Text style={styles.testBtnText}>Test Connection</Text>
                )}
              </Pressable>

              <InfoCollapsible
                label={`What is ${activeService.name} used for?`}
                content={activeService.description}
              />
            </>
          )}
        </BottomSheetView>
      </BottomSheet>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg.primary },
  scroll: { padding: spacing.xxl, gap: spacing.lg, paddingBottom: 40 },
  title: { ...typography.heading, color: colors.text.primary },
  subtitle: { ...typography.body, color: colors.text.secondary, marginTop: spacing.xs },
  progressBar: {
    height: 4,
    backgroundColor: colors.bg.tertiary,
    borderRadius: 2,
    overflow: 'hidden',
    marginTop: spacing.lg,
  },
  progressFill: { height: '100%', backgroundColor: colors.accent, borderRadius: 2 },
  progressText: { ...typography.caption, color: colors.text.tertiary },
  list: { gap: spacing.sm },
  serviceRow: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: spacing.lg,
    backgroundColor: colors.bg.secondary,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.border,
    gap: spacing.md,
    minHeight: 72,
  },
  emoji: { fontSize: 24 },
  serviceInfo: { flex: 1 },
  serviceName: { ...typography.subheading, color: colors.text.primary },
  serviceStatus: { ...typography.caption, color: colors.text.secondary, marginTop: 2 },
  chevron: { color: colors.text.tertiary, fontSize: 20 },
  continueBtn: {
    backgroundColor: colors.accent,
    paddingVertical: spacing.lg,
    borderRadius: 14,
    alignItems: 'center',
    minHeight: 56,
    justifyContent: 'center',
    marginTop: spacing.lg,
  },
  continueBtnDisabled: { opacity: 0.4 },
  continueBtnText: { ...typography.subheading, color: colors.white, fontSize: 17 },
  sheet: { flex: 1, padding: spacing.xxl, gap: spacing.lg },
  sheetTitle: { ...typography.heading, color: colors.text.primary },
  sheetHelp: { ...typography.body, color: colors.text.secondary },
  keyInput: {
    ...typography.body,
    color: colors.text.primary,
    backgroundColor: colors.bg.tertiary,
    borderRadius: 10,
    padding: spacing.md,
    borderWidth: 1,
    borderColor: colors.border,
    minHeight: 52,
  },
  resultBanner: {
    padding: spacing.md,
    borderRadius: 8,
  },
  testBtn: {
    backgroundColor: colors.accent,
    paddingVertical: spacing.md,
    borderRadius: 12,
    alignItems: 'center',
    minHeight: 52,
    justifyContent: 'center',
  },
  testBtnText: { ...typography.subheading, color: colors.white },
  disabled: { opacity: 0.5 },
});
