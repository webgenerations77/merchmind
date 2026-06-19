import { apiClient, isMock } from './client';
import type { OnboardingStatus, ValidateKeyResult, ApiEnvelope } from '../types/api';

export async function getOnboardingStatus(): Promise<OnboardingStatus> {
  if (isMock) {
    return {
      connected: {
        anthropic: false,
        openai: false,
        replicate: false,
        printify: false,
        shopify: false,
        supabase: false,
        klaviyo: false,
        expo: false,
      },
      all_connected: false,
    };
  }
  const { data } = await apiClient.get<ApiEnvelope<OnboardingStatus>>('/onboarding/status');
  return data.data;
}

export async function validateKey(service: string, key: string): Promise<ValidateKeyResult> {
  if (isMock) {
    await new Promise(r => setTimeout(r, 1500));
    return { service, valid: true };
  }
  const { data } = await apiClient.post<ApiEnvelope<ValidateKeyResult>>('/onboarding/validate-key', {
    service,
    key,
  });
  return data.data;
}

export async function completeOnboarding(): Promise<void> {
  if (isMock) return;
  await apiClient.post('/onboarding/complete');
}
