import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import React, { useEffect } from 'react';
import { DashboardLayout } from './components/layout/DashboardLayout';
import { Landing } from './pages/Landing';
import { Overview } from './pages/Overview';
import { Commands } from './pages/Commands';
import { Modules } from './pages/Modules';
import { Logging } from './pages/Logging';
import { Permissions } from './pages/Permissions';
import { Cases } from './pages/Cases';
import { Audit } from './pages/Audit';
import { Automod } from './pages/Automod';
import { AntiRaid } from './pages/AntiRaid';
import { Analytics } from './pages/Analytics';
import { Setup } from './pages/Setup';
import { Settings } from './pages/Settings';
import { useAppStore } from './store/useAppStore';
import { ErrorBoundary } from './components/ui/ErrorBoundary';

function AuthGuard({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAppStore();

  if (loading) {
    return (
      <div className="min-h-screen bg-app-bg flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="w-10 h-10 border-3 border-indigo-200 border-t-indigo-600 rounded-full animate-spin" />
          <p className="text-sm text-slate-500 font-medium">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}

export default function App() {
  const { initialize, user, loading } = useAppStore();

  useEffect(() => {
    initialize();
  }, [initialize]);

  return (
    <ErrorBoundary>
      <BrowserRouter>
        <Routes>
          {/* Landing page at root - shown when not logged in */}
          <Route
            path="/"
            element={
              loading ? (
                <div className="min-h-screen bg-app-bg flex items-center justify-center">
                  <div className="flex flex-col items-center gap-4">
                    <div className="w-10 h-10 border-3 border-indigo-200 border-t-indigo-600 rounded-full animate-spin" />
                    <p className="text-sm text-slate-500 font-medium">Loading...</p>
                  </div>
                </div>
              ) : user ? (
                <Navigate to="/dashboard" replace />
              ) : (
                <Landing />
              )
            }
          />

          {/* Protected dashboard routes */}
          <Route
            path="/dashboard"
            element={
              <AuthGuard>
                <DashboardLayout />
              </AuthGuard>
            }
          >
            <Route index element={<Overview />} />
            <Route path="commands" element={<Commands />} />
            <Route path="modules" element={<Modules />} />
            <Route path="setup" element={<Setup />} />
            <Route path="automod" element={<Automod />} />
            <Route path="anti-raid" element={<AntiRaid />} />
            <Route path="logging" element={<Logging />} />
            <Route path="permissions" element={<Permissions />} />
            <Route path="cases" element={<Cases />} />
            <Route path="audit" element={<Audit />} />
            <Route path="analytics" element={<Analytics />} />
            <Route path="settings" element={<Settings />} />
          </Route>

          {/* Catch-all redirect */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </ErrorBoundary>
  );
}
