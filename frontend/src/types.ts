export type EmailStatus = 'pending' | 'sending' | 'sent' | 'failed' | 'skipped';

export interface Recipient {
  row_index: number;
  name?: string;
  email: string;
  company?: string;
  is_valid: boolean;
  is_duplicate: boolean;
  status: EmailStatus;
  error_message?: string;
  sent_at?: string;
}

export interface ParsedContacts {
  total_rows: number;
  valid_count: number;
  invalid_count: number;
  duplicate_count: number;
  recipients: Recipient[];
  columns: string[];
  detected_email_column?: string;
  detected_name_column?: string;
  detected_company_column?: string;
}

export interface AttachmentInfo {
  attachment_id: string;
  filename: string;
  size_mb: number;
}

export interface CampaignStatus {
  campaign_id: string;
  status: 'pending' | 'running' | 'completed' | 'cancelled' | 'failed';
  total: number;
  sent: number;
  failed: number;
  skipped: number;
  pending: number;
  current_recipient?: string;
  recipients: Recipient[];
  started_at?: string;
  completed_at?: string;
  subject?: string;
  attachment_name?: string;
}

export interface AuthStatus {
  connected: boolean;
  email?: string;
  name?: string;
}

export type Step = 'gmail' | 'contacts' | 'compose' | 'attachment' | 'preview' | 'send' | 'results';
