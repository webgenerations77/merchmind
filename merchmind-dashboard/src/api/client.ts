import axios, { AxiosError } from 'axios';

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  timeout: 30000,
  headers: {
    'X-API-Key': import.meta.env.VITE_API_KEY || '',
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const config = error.config as typeof error.config & { _retryCount?: number };
    if (!config) return Promise.reject(error);

    const isServerError = !error.response || error.response.status >= 500;
    config._retryCount = config._retryCount ?? 0;

    if (isServerError && config._retryCount < 3) {
      config._retryCount += 1;
      const delay = Math.pow(2, config._retryCount) * 500;
      await new Promise((r) => setTimeout(r, delay));
      return apiClient(config);
    }

    return Promise.reject(error);
  },
);

export default apiClient;
