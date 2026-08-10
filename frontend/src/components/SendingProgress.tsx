import React, { useEffect, useRef } from 'react';
import { CheckCircle2, XCircle, Clock, Loader2, SkipForward, StopCircle } from 'lucide-react';
import { getCampaignStatus, cancelCampaign } from '../api';
import type { CampaignStatus, EmailStatus } from '../types';

interface SendingProgressProps {
  campaignId: string;
  onComplete: (status: CampaignStatus) => void;
}

const StatusIcon: React.FC<{ status: EmailStatus }> = ({ status }) => {
  switch (status) {
    case 'sent':     return <CheckCircle2 size={14} className="text-green-500 shrink-0" />;
    case 'failed':   return <XCircle size={14} className="text-red-500 shrink-0" />;
    case 'sending':  return <Loader2 size={14} className="text-blue-500 animate-spin shrink-0" />;
    case 'skipped':  return <SkipForward size={14} className="text-gray-400 shrink-0" />;
    default:         return <Clock size={14} className="text-gray-300 shrink-0" />;
  }
};

const statusLabel: Record<EmailStatus, string> = {
  sent: 'Sent',
  failed: 'Failed',
  sending: 'Sending…',
  skipped: 'Skipped',
  pending: 'Pending',
};

const statusRowColor: Record<EmailStatus, string> = {
  sent: '',
  failed: 'bg-red-50',
  sending: 'bg-blue-50',
  skipped: 'bg-gray-50',
  pending: '',
};

export const SendingProgress: React.FC<SendingProgressProps> = ({ campaignId, onComplete }) => {
  const [campaign, setCampaign] = React.useState<CampaignStatus | null>(null);
  const [cancelling, setCancelling] = React.useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const poll = async () => {
    try {
      const status = await getCampaignStatus(campaignId);
      setCampaign(status);
      if (status.status === 'completed' || status.status === 'cancelled' || status.status === 'failed') {
        clearInterval(intervalRef.current!);
        onComplete(status);
      }
    } catch {}
  };

  useEffect(() => {
    poll();
    intervalRef.current = setInterval(poll, 1500);
    return () => clearInterval(intervalRef.current!);
  }, [campaignId]);

  const handleCancel = async () => {
    setCancelling(true);
    try {
      await cancelCampaign(campaignId);
    } catch {}
    setCancelling(false);
  };

  if (!campaign) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="animate-spin text-blue-600" size={32} />
      </div>
    );
  }

  const percent = campaign.total > 0
    ? Math.round(((campaign.sent + campaign.failed + campaign.skipped) / campaign.total) * 100)
    : 0;

  const isRunning = campaign.status === 'running';

  return (
    <div className="max-w-2xl mx-auto py-6 px-4 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-gray-900">
            {isRunning ? 'Sending Emails…' : campaign.status === 'cancelled' ? 'Cancelled' : 'Send Complete'}
          </h2>
          <p className="text-sm text-gray-500 mt-0.5">
            {isRunning && campaign.current_recipient
              ? `Currently sending to: ${campaign.current_recipient}`
              : `${campaign.sent + campaign.failed + campaign.skipped} of ${campaign.total} processed`}
          </p>
        </div>
        {isRunning && (
          <button
            onClick={handleCancel}
            disabled={cancelling}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-red-600 border border-red-200 rounded-lg hover:bg-red-50 transition"
          >
            <StopCircle size={14} />
            {cancelling ? 'Cancelling…' : 'Cancel'}
          </button>
        )}
      </div>

      {/* Progress bar */}
      <div>
        <div className="flex justify-between text-xs text-gray-500 mb-1">
          <span>Sending {campaign.sent + campaign.failed + campaign.skipped} / {campaign.total}</span>
          <span>{percent}%</span>
        </div>
        <div className="w-full h-2.5 bg-gray-200 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${
              campaign.status === 'cancelled' ? 'bg-gray-400' : 'bg-blue-600'
            }`}
            style={{ width: `${percent}%` }}
          />
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-4 gap-3">
        <MiniStat label="Sent" value={campaign.sent} color="green" />
        <MiniStat label="Failed" value={campaign.failed} color="red" />
        <MiniStat label="Skipped" value={campaign.skipped} color="gray" />
        <MiniStat label="Pending" value={campaign.pending} color="blue" />
      </div>

      {/* Recipient list */}
      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
        <div className="max-h-80 overflow-y-auto">
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-gray-50 border-b border-gray-100">
              <tr className="text-xs text-gray-500 uppercase tracking-wide">
                <th className="px-4 py-2.5 text-left">Email</th>
                <th className="px-4 py-2.5 text-left">Name</th>
                <th className="px-4 py-2.5 text-left">Status</th>
                <th className="px-4 py-2.5 text-left">Error</th>
              </tr>
            </thead>
            <tbody>
              {campaign.recipients.map(r => (
                <tr key={r.row_index} className={`border-t border-gray-50 ${statusRowColor[r.status]}`}>
                  <td className="px-4 py-2 font-mono text-xs text-gray-800">{r.email}</td>
                  <td className="px-4 py-2 text-gray-600">{r.name || '—'}</td>
                  <td className="px-4 py-2">
                    <div className="flex items-center gap-1.5">
                      <StatusIcon status={r.status} />
                      <span className={`text-xs font-medium ${
                        r.status === 'sent' ? 'text-green-600' :
                        r.status === 'failed' ? 'text-red-600' :
                        r.status === 'sending' ? 'text-blue-600' :
                        'text-gray-400'
                      }`}>{statusLabel[r.status]}</span>
                    </div>
                  </td>
                  <td className="px-4 py-2 text-xs text-red-500 max-w-xs truncate">{r.error_message || ''}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

const MiniStat: React.FC<{ label: string; value: number; color: string }> = ({ label, value, color }) => {
  const colors: Record<string, string> = {
    green: 'bg-green-50 border-green-200 text-green-700',
    red: 'bg-red-50 border-red-200 text-red-700',
    gray: 'bg-gray-50 border-gray-200 text-gray-600',
    blue: 'bg-blue-50 border-blue-200 text-blue-700',
  };
  return (
    <div className={`border rounded-lg p-3 text-center ${colors[color] || colors.gray}`}>
      <div className="text-xl font-bold">{value}</div>
      <div className="text-xs font-medium opacity-70 mt-0.5">{label}</div>
    </div>
  );
};
