import React from 'react';
import { SafeAreaView, StyleSheet } from 'react-native';
import { colors } from '../../theme';
import ConnectToolsScreen from '../onboarding/ConnectToolsScreen';
import type { ApiKeysScreenProps } from '../../navigation/types';

// Reuse the ConnectToolsScreen component for managing API keys post-onboarding
export default function ApiKeysScreen({ navigation }: ApiKeysScreenProps) {
  // Pass a compatible navigation shape; ConnectToolsScreen only calls navigate('PickNiches')
  // which we override here to just go back
  const adaptedNav = {
    ...navigation,
    navigate: (screen: string) => {
      if (screen === 'PickNiches') navigation.goBack();
    },
  };

  return (
    <SafeAreaView style={styles.container} edges={['bottom']}>
      <ConnectToolsScreen navigation={adaptedNav as never} route={{} as never} />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg.primary },
});
