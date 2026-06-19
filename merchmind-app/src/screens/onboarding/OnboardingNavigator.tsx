import React from 'react';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { colors } from '../../theme';
import WelcomeScreen from './WelcomeScreen';
import ConnectToolsScreen from './ConnectToolsScreen';
import PickNichesScreen from './PickNichesScreen';
import PricingScreen from './PricingScreen';
import ScheduleScreen from './ScheduleScreen';
import BatchProgressScreen from './BatchProgressScreen';
import type { OnboardingStackParamList } from '../../navigation/types';

const Stack = createNativeStackNavigator<OnboardingStackParamList>();

export function OnboardingNavigator() {
  return (
    <Stack.Navigator
      screenOptions={{
        headerStyle: { backgroundColor: colors.bg.primary },
        headerTintColor: colors.text.primary,
        headerShadowVisible: false,
        headerBackTitle: 'Back',
        animation: 'slide_from_right',
      }}
    >
      <Stack.Screen name="Welcome" component={WelcomeScreen} options={{ headerShown: false }} />
      <Stack.Screen name="ConnectTools" component={ConnectToolsScreen} options={{ title: 'Connect Tools' }} />
      <Stack.Screen name="PickNiches" component={PickNichesScreen} options={{ title: 'Pick Niches' }} />
      <Stack.Screen name="Pricing" component={PricingScreen} options={{ title: 'Pricing' }} />
      <Stack.Screen name="Schedule" component={ScheduleScreen} options={{ title: 'Schedule' }} />
      <Stack.Screen name="BatchProgress" component={BatchProgressScreen} options={{ title: 'First Batch', headerBackVisible: false }} />
    </Stack.Navigator>
  );
}
