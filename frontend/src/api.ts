import axios from 'axios';
import type { ParsedContacts, AttachmentInfo, CampaignStatus, AuthStatus, Recipient } from './types';

// In production (Vercel), VITE_API_URL points to the Render backend.
// In dev, Vite's proxy forwards /api → http://localhost:8000
const BASE_URL = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}/api`
  : '/api';

// Store session token in localStorage for cross-origin deployments
const TOKEN_KEY = 'hr_mailer_token';

export const getStoredToken = (): string | null => localStorage.getItem(TOKEN_KEY);
export const setStoredToken = (token: string) => localStorage.setItem(TOKEN_KEY, token);
export const clearStoredToken = () => localStorage.removeItem(TOKEN_KEY);

const api = axios.create({
  baseURL: BASE_URL,
  withCredentials: true,
});

// Attach Bearer token to every request if available
api.interceptors.request.use(config => {
  const token = getStoredToken();
  if (token) {
    config.headers['Authorization'] = `Bearer ${token}`;
  }
  return config;
});

// Auth
export const getAuthStatus = (): Promise<AuthStatus> =>
  api.get('/auth/status').then(r => r.data);

export const initiateGoogleAuth = () => {
  const authUrl = import.meta.env.VITE_API_URL
    ? `${import.meta.env.VITE_API_URL}/api/auth/google`
    : '/api/auth/google';
  window.location.href = authUrl;
};

export const logout = (): Promise<void> =>
  api.post('/auth/logout').then(() => { clearStoredToken(); });

// Upload
export const uploadContacts = (file: File, emailColumn?: string): Promise<ParsedContacts> => {
  const form = new FormData();
  form.append('file', file);
  if (emailColumn) form.append('email_column', emailColumn);
  return api.post('/upload/contacts', form).then(r => r.data);
};

export const uploadAttachment = (file: File): Promise<AttachmentInfo> => {
  const form = new FormData();
  form.append('file', file);
  return api.post('/upload/attachment', form).then(r => r.data);
};

export const deleteAttachment = (id: string): Promise<void> =>
  api.delete(`/upload/attachment/${id}`).then(() => undefined);

// Email
export const previewEmail = (
  subject: string,
  body: string,
  recipient: Recipient
) =>
  api.post('/email/preview', { subject, body, recipient }).then(r => r.data);

export const sendCampaign = (payload: {
  subject: string;
  body: string;
  recipients: Recipient[];
  attachment_id?: string;
  delay_seconds?: number;
}): Promise<{ campaign_id: string; total: number }> =>
  api.post('/email/send_full', payload).then(r => r.data);

export const getCampaignStatus = (id: string): Promise<CampaignStatus> =>
  api.get(`/email/status/${id}`).then(r => r.data);

export const cancelCampaign = (id: string): Promise<void> =>
  api.post(`/email/cancel/${id}`).then(() => undefined);

export const retryFailed = (campaign_id: string): Promise<{ campaign_id: string }> =>
  api.post('/email/retry', { campaign_id }).then(r => r.data);

export const exportResults = (campaign_id: string) => {
  const base = import.meta.env.VITE_API_URL
    ? `${import.meta.env.VITE_API_URL}/api`
    : '/api';
  window.location.href = `${base}/email/export/${campaign_id}`;
};

export const healthCheck = () =>
  api.get('/health').then(r => r.data);
