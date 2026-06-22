import React from 'react';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { Text, View } from 'react-native';
import { colors } from '../theme';
import { useReviewStore } from '../store/reviewStore';
import type {
  MainTabParamList,
  HomeStackParamList,
  ReviewStackParamList,
  ProductsStackParamList,
} from './types';

// Screens
import HomeScreen from '../screens/home/HomeScreen';
import SettingsScreen from '../screens/settings/SettingsScreen';
import ApiKeysScreen from '../screens/settings/ApiKeysScreen';
import PricingRulesScreen from '../screens/settings/PricingRulesScreen';
import NicheClustersScreen from '../screens/settings/NicheClustersScreen';
import ScheduleSettingsScreen from '../screens/settings/ScheduleSettingsScreen';

import ReviewQueueScreen from '../screens/review/ReviewQueueScreen';
import ReviewCardScreen from '../screens/review/ReviewCardScreen';
import BatchCompleteScreen from '../screens/review/BatchCompleteScreen';

import PublishQueueScreen from '../screens/queue/PublishQueueScreen';
import LiveProductsScreen from '../screens/products/LiveProductsScreen';
import ProductDetailScreen from '../screens/products/ProductDetailScreen';
import AnalyticsScreen from '../screens/analytics/AnalyticsScreen';

const Tab = createBottomTabNavigator<MainTabParamList>();
const HomeStack = createNativeStackNavigator<HomeStackParamList>();
const ReviewStack = createNativeStackNavigator<ReviewStackParamList>();
const ProductsStack = createNativeStackNavigator<ProductsStackParamList>();

function TabIcon({ emoji, focused }: { emoji: string; focused: boolean }) {
  return (
    <Text style={{ fontSize: 22, opacity: focused ? 1 : 0.5 }}>{emoji}</Text>
  );
}

function HomeStackNavigator() {
  return (
    <HomeStack.Navigator
      screenOptions={{
        headerStyle: { backgroundColor: colors.bg.primary },
        headerTintColor: colors.text.primary,
        headerShadowVisible: false,
      }}
    >
      <HomeStack.Screen name="Home" component={HomeScreen} options={{ headerShown: false }} />
      <HomeStack.Screen name="Settings" component={SettingsScreen} options={{ title: 'Settings' }} />
      <HomeStack.Screen name="ApiKeys" component={ApiKeysScreen} options={{ title: 'API Keys' }} />
      <HomeStack.Screen name="PricingRules" component={PricingRulesScreen} options={{ title: 'Pricing Rules' }} />
      <HomeStack.Screen name="NicheClusters" component={NicheClustersScreen} options={{ title: 'Niche Clusters' }} />
      <HomeStack.Screen name="ScheduleSettings" component={ScheduleSettingsScreen} options={{ title: 'Schedule' }} />
    </HomeStack.Navigator>
  );
}

function ReviewStackNavigator() {
  return (
    <ReviewStack.Navigator
      screenOptions={{
        headerStyle: { backgroundColor: colors.bg.primary },
        headerTintColor: colors.text.primary,
        headerShadowVisible: false,
      }}
    >
      <ReviewStack.Screen name="ReviewQueue" component={ReviewQueueScreen} options={{ headerShown: false }} />
      <ReviewStack.Screen name="ReviewCard" component={ReviewCardScreen} options={{ headerShown: false }} />
      <ReviewStack.Screen name="BatchComplete" component={BatchCompleteScreen} options={{ headerShown: false }} />
    </ReviewStack.Navigator>
  );
}

function ProductsStackNavigator() {
  return (
    <ProductsStack.Navigator
      screenOptions={{
        headerStyle: { backgroundColor: colors.bg.primary },
        headerTintColor: colors.text.primary,
        headerShadowVisible: false,
      }}
    >
      <ProductsStack.Screen name="LiveProducts" component={LiveProductsScreen} options={{ headerShown: false }} />
      <ProductsStack.Screen name="ProductDetail" component={ProductDetailScreen} options={{ headerShown: false }} />
    </ProductsStack.Navigator>
  );
}

function ReviewBadge({ count }: { count: number }) {
  if (count === 0) return null;
  return (
    <View
      style={{
        position: 'absolute',
        top: -4,
        right: -8,
        backgroundColor: '#EF4444',
        borderRadius: 10,
        minWidth: 18,
        height: 18,
        alignItems: 'center',
        justifyContent: 'center',
        paddingHorizontal: 4,
      }}
    >
      <Text style={{ color: colors.white, fontSize: 11, fontWeight: '700' }}>{count}</Text>
    </View>
  );
}

export function MainTabNavigator() {
  const queue = useReviewStore(s => s.queue);
  const pendingCount = queue.filter(d => d.status === 'ready').length;

  return (
    <Tab.Navigator
      screenOptions={{
        tabBarStyle: {
          backgroundColor: colors.bg.secondary,
          borderTopColor: colors.border,
          borderTopWidth: 1,
        },
        tabBarActiveTintColor: colors.accent,
        tabBarInactiveTintColor: colors.text.tertiary,
        headerShown: false,
      }}
    >
      <Tab.Screen
        name="ReviewTab"
        component={ReviewStackNavigator}
        options={{
          tabBarLabel: 'Review',
          tabBarIcon: ({ focused }) => (
            <View>
              <TabIcon emoji="✅" focused={focused} />
              <ReviewBadge count={pendingCount} />
            </View>
          ),
          tabBarBadge: pendingCount > 0 ? pendingCount : undefined,
        }}
      />
      <Tab.Screen
        name="HomeTab"
        component={HomeStackNavigator}
        options={{
          tabBarLabel: 'Home',
          tabBarIcon: ({ focused }) => <TabIcon emoji="🏠" focused={focused} />,
        }}
      />
      <Tab.Screen
        name="QueueTab"
        component={PublishQueueScreen}
        options={{
          tabBarLabel: 'Queue',
          tabBarIcon: ({ focused }) => <TabIcon emoji="📤" focused={focused} />,
        }}
      />
      <Tab.Screen
        name="ProductsTab"
        component={ProductsStackNavigator}
        options={{
          tabBarLabel: 'Products',
          tabBarIcon: ({ focused }) => <TabIcon emoji="🛍️" focused={focused} />,
        }}
      />
      <Tab.Screen
        name="AnalyticsTab"
        component={AnalyticsScreen}
        options={{
          tabBarLabel: 'Analytics',
          tabBarIcon: ({ focused }) => <TabIcon emoji="📊" focused={focused} />,
        }}
      />
    </Tab.Navigator>
  );
}
