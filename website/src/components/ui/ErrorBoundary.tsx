import { useEffect, useState, type ReactNode } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface ErrorBoundaryProps {
  children: ReactNode;
}

export function ErrorBoundary({ children }: ErrorBoundaryProps) {
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    const onError = (event: ErrorEvent) => {
      setErrorMessage(event.error?.message || event.message || 'Unknown rendering error');
    };

    const onUnhandledRejection = (event: PromiseRejectionEvent) => {
      const reason = event.reason;
      if (reason instanceof Error) {
        setErrorMessage(reason.message);
      } else if (typeof reason === 'string') {
        setErrorMessage(reason);
      } else {
        setErrorMessage('Unhandled promise rejection');
      }
    };

    window.addEventListener('error', onError);
    window.addEventListener('unhandledrejection', onUnhandledRejection);

    return () => {
      window.removeEventListener('error', onError);
      window.removeEventListener('unhandledrejection', onUnhandledRejection);
    };
  }, []);

  if (errorMessage) {
    return (
      <div className="min-h-screen bg-app-bg flex items-center justify-center px-6">
        <div className="max-w-lg w-full bg-card-bg border border-cream-300 rounded-3xl p-8 shadow-[0_20px_60px_-15px_rgba(0,0,0,0.1)]">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2.5 bg-red-50 text-red-600 rounded-xl">
              <AlertTriangle className="w-5 h-5" />
            </div>
            <h1 className="text-lg font-display font-bold text-slate-800">Dashboard Error</h1>
          </div>
          <p className="text-sm text-slate-600 mb-6">
            A page error occurred. Refresh to recover. If this keeps happening, the backend data for this view is malformed.
          </p>
          <div className="mb-6 p-3 bg-cream-50 border border-cream-200 rounded-xl text-xs text-slate-600 font-mono break-all">
            {errorMessage}
          </div>
          <button
            onClick={() => window.location.reload()}
            className="inline-flex items-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold rounded-xl transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            Reload Dashboard
          </button>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
