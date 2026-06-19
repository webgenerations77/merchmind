import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import type { BottomTabScreenProps } from '@react-navigation/bottom-tabs';
import type { CompositeScreenProps } from '@react-navigation/native';

// ─── Root ─────────────────────────────────────────────────────────────────────

export type RootStackParamList = {
  Onboarding: undefined;
  Main: undefined;
};

// ─── Onboarding ───────────────────────────────────────────────────────────────

export type OnboardingStackParamList = {
  Welcome: undefined;
  ConnectTools: undefined;
  PickNiches: undefined;
  Pricing: undefined;
  Schedule: undefined;
  BatchProgress: { batchId: string };
};

// ─── Main Tab ─────────────────────────────────────────────────────────────────

export type MainTabParamList = {
  HomeTab: undefined;
  ReviewTab: undefined;
  QueueTab: undefined;
  ProductsTab: undefined;
  AnalyticsTab: undefined;
};

// ─── Home Stack ───────────────────────────────────────────────────────────────

export type HomeStackParamList = {
  Home: undefined;
  Settings: undefined;
  ApiKeys: undefined;
  PricingRules: undefined;
  NicheClusters: undefined;
  ScheduleSettings: undefined;
};

// ─── Review Stack ─────────────────────────────────────────────────────────────

export type ReviewStackParamList = {
  ReviewQueue: undefined;
  ReviewCard: { designId: string; index: number };
  BatchComplete: undefined;
};

// ─── Products Stack ───────────────────────────────────────────────────────────

export type ProductsStackParamList = {
  LiveProducts: undefined;
  ProductDetail: { productId: string };
};

// ─── Screen prop types ────────────────────────────────────────────────────────

export type HomeScreenProps = NativeStackScreenProps<HomeStackParamList, 'Home'>;
export type SettingsScreenProps = NativeStackScreenProps<HomeStackParamList, 'Settings'>;
export type ApiKeysScreenProps = NativeStackScreenProps<HomeStackParamList, 'ApiKeys'>;
export type PricingRulesScreenProps = NativeStackScreenProps<HomeStackParamList, 'PricingRules'>;
export type NicheClustersScreenProps = NativeStackScreenProps<HomeStackParamList, 'NicheClusters'>;
export type ScheduleSettingsScreenProps = NativeStackScreenProps<HomeStackParamList, 'ScheduleSettings'>;

export type ReviewQueueScreenProps = NativeStackScreenProps<ReviewStackParamList, 'ReviewQueue'>;
export type ReviewCardScreenProps = NativeStackScreenProps<ReviewStackParamList, 'ReviewCard'>;
export type BatchCompleteScreenProps = NativeStackScreenProps<ReviewStackParamList, 'BatchComplete'>;

export type LiveProductsScreenProps = NativeStackScreenProps<ProductsStackParamList, 'LiveProducts'>;
export type ProductDetailScreenProps = NativeStackScreenProps<ProductsStackParamList, 'ProductDetail'>;

export type OnboardingWelcomeProps = NativeStackScreenProps<OnboardingStackParamList, 'Welcome'>;
export type OnboardingConnectToolsProps = NativeStackScreenProps<OnboardingStackParamList, 'ConnectTools'>;
export type OnboardingPickNichesProps = NativeStackScreenProps<OnboardingStackParamList, 'PickNiches'>;
export type OnboardingPricingProps = NativeStackScreenProps<OnboardingStackParamList, 'Pricing'>;
export type OnboardingScheduleProps = NativeStackScreenProps<OnboardingStackParamList, 'Schedule'>;
export type OnboardingBatchProgressProps = NativeStackScreenProps<OnboardingStackParamList, 'BatchProgress'>;
