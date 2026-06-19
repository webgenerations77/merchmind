import { useState, useCallback } from 'react';
import { validateKey } from '../api/onboarding';
import type { ValidateKeyResult } from '../types/api';

interface UseApiKeyState {
  isValidating: boolean;
  result: ValidateKeyResult | null;
  validate: (service: string, key: string) => Promise<ValidateKeyResult>;
  reset: () => void;
}

export function useApiKey(): UseApiKeyState {
  const [isValidating, setIsValidating] = useState(false);
  const [result, setResult] = useState<ValidateKeyResult | null>(null);

  const validate = useCallback(async (service: string, key: string): Promise<ValidateKeyResult> => {
    setIsValidating(true);
    setResult(null);
    try {
      const res = await validateKey(service, key);
      setResult(res);
      return res;
    } finally {
      setIsValidating(false);
    }
  }, []);

  const reset = useCallback(() => {
    setResult(null);
  }, []);

  return { isValidating, result, validate, reset };
}
