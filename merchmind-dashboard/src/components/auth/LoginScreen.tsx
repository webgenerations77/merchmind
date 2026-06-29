import { useState } from 'react';
import { signInWithGoogle } from '../../firebase';
import Logo from '../brand/Logo';
import LogoMark from '../brand/LogoMark';

export default function LoginScreen() {
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSignIn = async () => {
    setLoading(true);
    setError('');
    try {
      await signInWithGoogle();
    } catch (e) {
      setError((e as Error).message);
    }
    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-violet-mesh flex items-center justify-center p-4 relative overflow-hidden">
      <LogoMark size={420} className="absolute -left-24 -bottom-24 opacity-[0.06] pointer-events-none select-none" />
      <div className="relative bg-bg-secondary border border-border rounded-2xl p-8 w-full max-w-sm text-center shadow-[0_1px_2px_rgba(21,19,43,.08),0_18px_44px_rgba(21,19,43,.08)]">
        <div className="flex justify-center mb-2">
          <Logo markSize={40} wordmarkClassName="text-2xl" />
        </div>
        <p className="text-sm text-text-tertiary mb-8">Spinach The Cow Merch Pipe</p>

        <button
          onClick={handleSignIn}
          disabled={loading}
          className="w-full flex items-center justify-center gap-3 px-4 py-3 rounded-lg bg-white text-gray-800 font-medium text-sm hover:bg-gray-100 transition-colors disabled:opacity-50"
        >
          <svg width="18" height="18" viewBox="0 0 18 18" xmlns="http://www.w3.org/2000/svg">
            <path d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844a4.14 4.14 0 0 1-1.796 2.716v2.259h2.908c1.702-1.567 2.684-3.875 2.684-6.615Z" fill="#4285F4"/>
            <path d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18Z" fill="#34A853"/>
            <path d="M3.964 10.71A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.997 8.997 0 0 0 0 9c0 1.452.348 2.827.957 4.042l3.007-2.332Z" fill="#FBBC05"/>
            <path d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.958L3.964 7.29C4.672 5.163 6.656 3.58 9 3.58Z" fill="#EA4335"/>
          </svg>
          {loading ? 'Signing in...' : 'Sign in with Google'}
        </button>

        {error && (
          <p className="mt-4 text-sm text-confidence-low">{error}</p>
        )}

        <p className="mt-6 text-xs text-text-tertiary">Authorized accounts only</p>
      </div>
    </div>
  );
}
