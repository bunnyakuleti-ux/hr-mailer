import React, { useEffect, useState } from 'react';
import { Mail, CheckCircle, AlertCircle, LogOut, Loader2, ExternalLink } from 'lucide-react';
import { getAuthStatus, initiateGoogleAuth, logout } from '../api';
import type { AuthStatus } from '../types';

interface GmailConnectProps {
  onConnected: (status: AuthStatus) => void;
}

export const GmailConnect: React.FC<GmailConnectProps> = ({ onConnected }) => {
  const [auth, setAuth] = useState<AuthStatus>({ connected: false });
  const [loading, setLoading] = useState(true);
  const [loggingOut, setLoggingOut] = useState(false);

  const fetchStatus = async () => {
    try {
      setLoading(true);
      const status = await getAuthStatus();
      setAuth(status);
      if (status.connected) onConnected(status);
    } catch {
      setAuth({ connected: false });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    // Check for auth success/error in URL
    const params = new URLSearchParams(window.location.search);
    if (params.get('auth_success')) {
      window.history.replaceState({}, '', window.location.pathname);
      fetchStatus();
    }
    if (params.get('auth_error')) {
      window.history.replaceState({}, '', window.location.pathname);
    }
  }, []);

  const handleLogout = async () => {
    setLoggingOut(true);
    try {
      await logout();
      setAuth({ connected: false });
    } finally {
      setLoggingOut(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="animate-spin text-blue-600" size={32} />
      </div>
    );
  }

  return (
    <div className="max-w-xl mx-auto py-10 px-4">
      <div className="text-center mb-8">
        <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-50 rounded-full mb-4">
          <Mail size={32} className="text-blue-600" />
        </div>
        <h2 className="text-2xl font-bold text-gray-900">Connect Your Gmail</h2>
        <p className="mt-2 text-gray-500 text-sm">
          HR Mailer uses Google OAuth 2.0 — your password is never stored or seen.
        </p>
      </div>

      {auth.connected ? (
        <div className="bg-green-50 border border-green-200 rounded-xl p-6">
          <div className="flex items-start gap-3">
            <CheckCircle size={20} className="text-green-600 mt-0.5 shrink-0" />
            <div className="flex-1">
              <p className="font-semibold text-green-800">Gmail Connected</p>
              <p className="text-green-700 text-sm mt-0.5">{auth.email}</p>
              {auth.name && <p className="text-green-600 text-xs mt-0.5">{auth.name}</p>}
            </div>
          </div>
          <div className="mt-4 flex gap-3">
            <button
              onClick={handleLogout}
              disabled={loggingOut}
              className="flex items-center gap-2 px-4 py-2 text-sm bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition"
            >
              {loggingOut ? <Loader2 size={14} className="animate-spin" /> : <LogOut size={14} />}
              Disconnect
            </button>
          </div>
        </div>
      ) : (
        <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
          <div className="flex items-start gap-3 mb-5 p-3 bg-amber-50 rounded-lg border border-amber-100">
            <AlertCircle size={16} className="text-amber-600 mt-0.5 shrink-0" />
            <p className="text-xs text-amber-700">
              You'll be redirected to Google's secure sign-in. HR Mailer only requests permission to
              <strong> send emails</strong> on your behalf — nothing else.
            </p>
          </div>

          <button
            onClick={initiateGoogleAuth}
            className="w-full flex items-center justify-center gap-3 px-5 py-3 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg transition shadow-sm"
          >
            <svg width="18" height="18" viewBox="0 0 48 48" fill="none">
              <path d="M44.5 20H24v8.5h11.8C34.7 33.9 30.1 37 24 37c-7.2 0-13-5.8-13-13s5.8-13 13-13c3.1 0 5.9 1.1 8.1 2.9l6.4-6.4C34.6 4.1 29.6 2 24 2 11.8 2 2 11.8 2 24s9.8 22 22 22c11 0 21-8 21-22 0-1.3-.2-2.7-.5-4z" fill="#FFC107"/>
              <path d="M6.3 14.7l7 5.1C15.1 16.1 19.2 13 24 13c3.1 0 5.9 1.1 8.1 2.9l6.4-6.4C34.6 4.1 29.6 2 24 2 16.3 2 9.7 7.4 6.3 14.7z" fill="#FF3D00"/>
              <path d="M24 46c5.5 0 10.5-1.9 14.3-5.1l-6.6-5.6C29.5 36.8 26.9 37.9 24 37.9c-6.1 0-10.7-3.1-11.8-8.4l-7 5.4C8.1 41.7 15.5 46 24 46z" fill="#4CAF50"/>
              <path d="M44.5 20H24v8.5h11.8c-.6 2.2-2 4.1-3.8 5.4l6.6 5.6C42.4 35.9 45 30.4 45 24c0-1.3-.2-2.7-.5-4z" fill="#1976D2"/>
            </svg>
            Sign in with Google
          </button>

          <p className="text-center text-xs text-gray-400 mt-4">
            Requires a valid Google Cloud project with Gmail API enabled.{' '}
            <a href="#setup" className="text-blue-500 hover:underline inline-flex items-center gap-0.5">
              Setup guide <ExternalLink size={10} />
            </a>
          </p>
        </div>
      )}
    </div>
  );
};
