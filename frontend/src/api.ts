import axios from 'axios';
import type { ParsedContacts, AttachmentInfo, CampaignStatus, AuthStatus, Recipient } from './types';

const BASE_URL = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}/api`
  : '/api';

const SESSION_KEY = 'hr_session';

export const saveSession = (token: string) => localStorage.setItem(SESSION_KEY, token);
export const clearSession = () => localStorage.removeItem(SESSION_KEY);
export const getSession = () => localStorage.getItem(SESSION_KEY);

const api = axios.create({ baseURL: BASE_URL, withCredentials: true });

// Attach session token as header on every request
api.interceptors.request.use(config => {
  const token = getSession();
  if (token) config.headers['X-Session-Token'] = token;
  return config;
});

// Auth
export const getAuthStatus = (): Promise<AuthStatus> =>
  api.get('/auth/status').then(r => r.data);

export const initiateGoogleAuth = () => {
  window.location.href = import.meta.env.VITE_API_URL
    ? `${import.meta.env.VITE_API_URL}/api/auth/google`
    : '/api/auth/google';
};

export const logout = (): Promise<void> =>
  api.post('/auth/logout').then(() => clearSession());

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
export const previewEmail = (subject: string, body: string, recipient: Recipient) =>
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
  const base = import.meta.env.VITE_API_URL ? `${import.meta.env.VITE_API_URL}/api` : '/api';
  const token = getSession();
  window.location.href = `${base}/email/export/${campaign_id}${token ? `?token=${token}` : ''}`;
};

export const healthCheck = () => api.get('/health').then(r => r.data);
