import axios, { AxiosInstance, AxiosError } from 'axios';
import Constants from 'expo-constants';

const extra = Constants.expoConfig?.extra ?? {};

const isMock = extra.USE_MOCK_API === 'true';

export function createApiClient(): AxiosInstance {
  const client = axios.create({
    baseURL: extra.API_BASE_URL || 'http://localhost:8000',
    timeout: 30000,
    headers: {
      'X-API-Key': extra.APP_API_KEY || '',
      'Content-Type': 'application/json',
    },
  });

  client.interceptors.request.use(config => {
    if (__DEV__) {
      console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`);
    }
    return config;
  });

  client.interceptors.response.use(
    response => response,
    async (error: AxiosError) => {
      const config = error.config as (typeof error.config & { _retryCount?: number });
      if (!config) return Promise.reject(error);

      if (error.response?.status === 401) {
        console.error('[API] Unauthorized — check APP_API_KEY');
        return Promise.reject(error);
      }

      const isServerError = !error.response || error.response.status >= 500;
      config._retryCount = config._retryCount ?? 0;

      if (isServerError && config._retryCount < 3) {
        config._retryCount += 1;
        const delay = Math.pow(2, config._retryCount) * 500;
        await new Promise(resolve => setTimeout(resolve, delay));
        return client(config);
      }

      return Promise.reject(error);
    },
  );

  return client;
}

export const apiClient = createApiClient();
export { isMock };
