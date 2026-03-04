import { Component, type ErrorInfo, type ReactNode } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  errorMessage: string | null;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = {
    errorMessage: null,
  };

  private onError = (event: ErrorEvent) => {
    this.setState({
      errorMessage: event.error?.message || event.message || 'Unknown rendering error',
    });
  };

  private onUnhandledRejection = (event: PromiseRejectionEvent) => {
    const reason = event.reason;
    if (reason instanceof Error) {
      this.setState({ errorMessage: reason.message });
      return;
    }
    if (typeof reason === 'string') {
      this.setState({ errorMessage: reason });
      return;
    }
    this.setState({ errorMessage: 'Unhandled promise rejection' });
  };

  static getDerivedStateFromError(error: unknown): ErrorBoundaryState {
    if (error instanceof Error) {
      return { errorMessage: error.message };
    }
    return { errorMessage: 'Unknown rendering error' };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Keep a breadcrumb in production logs for render failures.
    console.error('Dashboard render error:', error, errorInfo);
  }

  componentDidMount() {
    window.addEventListener('error', this.onError);
    window.addEventListener('unhandledrejection', this.onUnhandledRejection);
  }

  componentWillUnmount() {
    window.removeEventListener('error', this.onError);
    window.removeEventListener('unhandledrejection', this.onUnhandledRejection);
  }

  render() {
    if (this.state.errorMessage) {
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
              {this.state.errorMessage}
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

    return <>{this.props.children}</>;
  }
}
