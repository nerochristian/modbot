import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Bot, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import { useAppStore } from '@/store/useAppStore';

export function Callback() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const initialize = useAppStore((s) => s.initialize);
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [errorMsg, setErrorMsg] = useState('');

  useEffect(() => {
    const error = searchParams.get('error');

    if (error) {
      setStatus('error');
      setErrorMsg(error === 'access_denied' ? 'You denied the authorization request.' : `Discord returned an error: ${error}`);
      return;
    }

    async function finalizeLogin() {
      try {
        await initialize();
        setStatus('success');
        setTimeout(() => navigate('/dashboard', { replace: true }), 800);
      } catch (err) {
        setStatus('error');
        setErrorMsg(err instanceof Error ? err.message : 'Authentication failed');
      }
    }

    finalizeLogin();
  }, [searchParams, navigate, initialize]);

  return (
    <div className="min-h-screen bg-app-bg flex items-center justify-center">
      <div className="max-w-sm w-full bg-white rounded-3xl border border-cream-200 shadow-[0_20px_60px_-15px_rgba(0,0,0,0.08)] p-8 text-center">
        <div className="p-3 bg-indigo-50 rounded-2xl inline-flex mb-5">
          <Bot className="w-8 h-8 text-indigo-600" />
        </div>

        {status === 'loading' && (
          <>
            <Loader2 className="w-8 h-8 text-indigo-500 animate-spin mx-auto mb-4" />
            <h2 className="text-lg font-display font-bold text-slate-800 mb-2">Connecting to Discord</h2>
            <p className="text-sm text-slate-500">Authenticating your account...</p>
          </>
        )}

        {status === 'success' && (
          <>
            <CheckCircle className="w-8 h-8 text-emerald-500 mx-auto mb-4" />
            <h2 className="text-lg font-display font-bold text-slate-800 mb-2">Connected!</h2>
            <p className="text-sm text-slate-500">Redirecting to your dashboard...</p>
          </>
        )}

        {status === 'error' && (
          <>
            <AlertCircle className="w-8 h-8 text-red-500 mx-auto mb-4" />
            <h2 className="text-lg font-display font-bold text-slate-800 mb-2">Authentication Failed</h2>
            <p className="text-sm text-red-500 mb-6">{errorMsg}</p>
            <a
              href="/"
              className="inline-flex px-6 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold rounded-xl transition-colors text-sm"
            >
              Back to Home
            </a>
          </>
        )}
      </div>
    </div>
  );
}
