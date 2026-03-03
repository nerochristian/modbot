import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Bot, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import { useAppStore } from '@/store/useAppStore';

export function Callback() {
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const initialize = useAppStore(s => s.initialize);
    const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
    const [errorMsg, setErrorMsg] = useState('');

    useEffect(() => {
        const code = searchParams.get('code');
        const error = searchParams.get('error');

        if (error) {
            setStatus('error');
            setErrorMsg(error === 'access_denied' ? 'You denied the authorization request.' : `Discord returned an error: ${error}`);
            return;
        }

        if (!code) {
            setStatus('error');
            setErrorMsg('No authorization code received from Discord.');
            return;
        }

        // Exchange code for token with your backend
        async function exchangeCode() {
            try {
                // TODO: Replace with real API call when backend is ready
                // const response = await fetch('/api/auth/callback', {
                //   method: 'POST',
                //   headers: { 'Content-Type': 'application/json' },
                //   body: JSON.stringify({ code }),
                // });
                // if (!response.ok) throw new Error('Failed to authenticate');

                // For now, simulate success and initialize with mock data
                await new Promise(r => setTimeout(r, 1500));
                await initialize();
                setStatus('success');

                // Redirect to dashboard after brief success state
                setTimeout(() => navigate('/', { replace: true }), 1000);
            } catch (err) {
                setStatus('error');
                setErrorMsg(err instanceof Error ? err.message : 'Authentication failed');
            }
        }

        exchangeCode();
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
                            href="/landing"
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
