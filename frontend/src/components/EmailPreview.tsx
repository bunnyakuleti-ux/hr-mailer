import React, { useState, useEffect } from 'react';
import { ChevronLeft, ChevronRight, Paperclip } from 'lucide-react';
import type { Recipient, AttachmentInfo } from '../types';

interface EmailPreviewProps {
  subject: string;
  body: string;
  recipients: Recipient[];
  attachment: AttachmentInfo | null;
  fromEmail: string;
}

const replaceVars = (text: string, r: Recipient) =>
  text
    .replace(/\{\{name\}\}/g, r.name || '')
    .replace(/\{\{company\}\}/g, r.company || '')
    .replace(/\{\{email\}\}/g, r.email || '');

export const EmailPreview: React.FC<EmailPreviewProps> = ({
  subject, body, recipients, attachment, fromEmail,
}) => {
  const validRecipients = recipients.filter(r => r.is_valid && !r.is_duplicate);
  const [index, setIndex] = useState(0);
  const [preview, setPreview] = useState<{ subject: string; body: string } | null>(null);

  const current = validRecipients[index];

  useEffect(() => {
    if (!current) return;
    setPreview({
      subject: replaceVars(subject, current),
      body: replaceVars(body, current),
    });
  }, [index, subject, body, current]);

  if (!validRecipients.length) {
    return (
      <div className="max-w-2xl mx-auto py-10 text-center text-gray-500">
        No valid recipients to preview.
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto py-6 px-4 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-gray-900">Email Preview</h2>
          <p className="text-sm text-gray-500 mt-0.5">Review each personalized email before sending.</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setIndex(i => Math.max(0, i - 1))}
            disabled={index === 0}
            className="p-1.5 rounded-lg border border-gray-200 hover:bg-gray-50 disabled:opacity-40 transition"
          >
            <ChevronLeft size={16} />
          </button>
          <span className="text-sm font-medium text-gray-600 whitespace-nowrap">
            {index + 1} / {validRecipients.length}
          </span>
          <button
            onClick={() => setIndex(i => Math.min(validRecipients.length - 1, i + 1))}
            disabled={index === validRecipients.length - 1}
            className="p-1.5 rounded-lg border border-gray-200 hover:bg-gray-50 disabled:opacity-40 transition"
          >
            <ChevronRight size={16} />
          </button>
        </div>
      </div>

      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm">
        {/* Header */}
        <div className="bg-gray-50 px-5 py-3 border-b border-gray-100 space-y-2">
          <div className="flex items-center gap-2 text-sm">
            <span className="text-gray-400 w-16 text-right shrink-0">FROM</span>
            <span className="font-medium text-gray-700">{fromEmail || 'your-gmail@gmail.com'}</span>
          </div>
          <div className="flex items-start gap-2 text-sm">
            <span className="text-gray-400 w-16 text-right shrink-0">TO</span>
            <div>
              <span className="font-medium text-gray-800">{current.email}</span>
              {current.name && <span className="text-gray-400 ml-1">({current.name})</span>}
              {current.company && (
                <span className="ml-2 text-xs text-gray-400 bg-gray-100 px-1.5 py-0.5 rounded">{current.company}</span>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <span className="text-gray-400 w-16 text-right shrink-0">SUBJECT</span>
            <span className="font-semibold text-gray-900">{preview?.subject || subject}</span>
          </div>
          {attachment && (
            <div className="flex items-center gap-2 text-sm">
              <span className="text-gray-400 w-16 text-right shrink-0">ATTACH</span>
              <span className="inline-flex items-center gap-1.5 text-blue-700 bg-blue-50 px-2 py-0.5 rounded text-xs border border-blue-100">
                <Paperclip size={11} /> {attachment.filename} ({attachment.size_mb} MB)
              </span>
            </div>
          )}
        </div>

        {/* Body */}
        <div className="px-5 py-4">
          <pre className="whitespace-pre-wrap font-sans text-sm text-gray-800 leading-relaxed">
            {preview?.body || body}
          </pre>
        </div>
      </div>

      <div className="text-xs text-gray-400 text-center">
        Preview {index + 1} of {validRecipients.length} valid recipients
      </div>
    </div>
  );
};
