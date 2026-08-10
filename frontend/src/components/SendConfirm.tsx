import React, { useState } from 'react';
import { AlertTriangle, Send, Loader2, Paperclip, Users, Mail } from 'lucide-react';
import type { AttachmentInfo, Recipient } from '../types';

interface SendConfirmProps {
  recipients: Recipient[];
  subject: string;
  attachment: AttachmentInfo | null;
  delaySeconds: number;
  onDelayChange: (v: number) => void;
  onConfirm: () => void;
  onCancel: () => void;
  sending: boolean;
}

export const SendConfirm: React.FC<SendConfirmProps> = ({
  recipients,
  subject,
  attachment,
  delaySeconds,
  onDelayChange,
  onConfirm,
  onCancel,
  sending,
}) => {
  const [confirmed, setConfirmed] = useState(false);
  const validCount = recipients.filter(r => r.is_valid && !r.is_duplicate).length;

  return (
    <div className="max-w-lg mx-auto py-8 px-4">
      <div className="bg-white border border-gray-200 rounded-2xl overflow-hidden shadow-md">
        {/* Header */}
        <div className="bg-amber-50 border-b border-amber-100 px-6 py-4 flex items-center gap-3">
          <AlertTriangle size={20} className="text-amber-500 shrink-0" />
          <div>
            <h2 className="font-bold text-gray-900">Confirm Send</h2>
            <p className="text-xs text-gray-500 mt-0.5">Review before sending — this cannot be undone easily.</p>
          </div>
        </div>

        {/* Summary */}
        <div className="px-6 py-5 space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <SummaryItem icon={<Users size={16} />} label="Recipients" value={`${validCount} emails`} />
            <SummaryItem icon={<Mail size={16} />} label="Subject" value={subject || '(none)'} truncate />
            {attachment && (
              <SummaryItem
                icon={<Paperclip size={16} />}
                label="Attachment"
                value={`${attachment.filename} (${attachment.size_mb} MB)`}
                truncate
              />
            )}
          </div>

          {/* Delay setting */}
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-gray-700">
              Delay between emails: <span className="text-blue-600 font-semibold">{delaySeconds}s</span>
            </label>
            <input
              type="range"
              min={1}
              max={10}
              step={0.5}
              value={delaySeconds}
              onChange={e => onDelayChange(Number(e.target.value))}
              className="w-full accent-blue-600"
            />
            <div className="flex justify-between text-xs text-gray-400">
              <span>1s (faster)</span>
              <span>10s (safer)</span>
            </div>
            <p className="text-xs text-gray-400">
              Estimated time: ~{Math.ceil((validCount * delaySeconds) / 60)} minutes
            </p>
          </div>

          {/* Checkbox confirmation */}
          <label className="flex items-start gap-3 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={confirmed}
              onChange={e => setConfirmed(e.target.checked)}
              className="mt-0.5 accent-blue-600"
            />
            <span className="text-sm text-gray-700">
              I confirm I want to send <strong>{validCount} individual emails</strong> from my Gmail account.
              Each recipient will receive a separate email.
            </span>
          </label>
        </div>

        {/* Actions */}
        <div className="px-6 py-4 bg-gray-50 border-t border-gray-100 flex gap-3 justify-end">
          <button
            onClick={onCancel}
            disabled={sending}
            className="px-4 py-2 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-100 transition"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={!confirmed || sending || validCount === 0}
            className="flex items-center gap-2 px-5 py-2 text-sm bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition shadow-sm"
          >
            {sending ? (
              <><Loader2 size={15} className="animate-spin" /> Sending...</>
            ) : (
              <><Send size={15} /> Send {validCount} Emails</>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

const SummaryItem: React.FC<{
  icon: React.ReactNode;
  label: string;
  value: string;
  truncate?: boolean;
}> = ({ icon, label, value, truncate }) => (
  <div className="bg-gray-50 rounded-lg p-3 border border-gray-100">
    <div className="flex items-center gap-1.5 text-gray-500 text-xs mb-1">
      {icon} {label}
    </div>
    <p className={`text-sm font-semibold text-gray-800 ${truncate ? 'truncate' : ''}`}>{value}</p>
  </div>
);
