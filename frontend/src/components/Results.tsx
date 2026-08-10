import React from 'react';
import { CheckCircle2, XCircle, SkipForward, Download, RefreshCw, PlusCircle, Trophy } from 'lucide-react';
import { exportResults, retryFailed } from '../api';
import type { CampaignStatus } from '../types';
import toast from 'react-hot-toast';

interface ResultsProps {
  campaign: CampaignStatus;
  onRetry: (campaignId: string) => void;
  onNewCampaign: () => void;
}

export const Results: React.FC<ResultsProps> = ({ campaign, onRetry, onNewCampaign }) => {
  const [retrying, setRetrying] = React.useState(false);

  const failedCount = campaign.recipients.filter(r => r.status === 'failed').length;

  const handleRetry = async () => {
    setRetrying(true);
    try {
      const res = await retryFailed(campaign.campaign_id);
      toast.success(`Retrying ${failedCount} failed emails…`);
      onRetry(res.campaign_id);
    } catch (e: any) {
      toast.error(e.response?.data?.detail || 'Retry failed.');
    } finally {
      setRetrying(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto py-8 px-4 space-y-6">
      {/* Hero */}
      <div className="text-center">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-green-50 mb-3">
          <Trophy size={30} className="text-green-500" />
        </div>
        <h2 className="text-2xl font-bold text-gray-900">Campaign Complete</h2>
        <p className="text-gray-500 text-sm mt-1">
          Campaign ID: <span className="font-mono text-xs text-gray-400">{campaign.campaign_id}</span>
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <ResultStat icon={<CheckCircle2 size={18} className="text-green-500" />} label="Sent" value={campaign.sent} color="green" />
        <ResultStat icon={<XCircle size={18} className="text-red-500" />} label="Failed" value={campaign.failed} color="red" />
        <ResultStat icon={<SkipForward size={18} className="text-gray-400" />} label="Skipped" value={campaign.skipped} color="gray" />
        <ResultStat icon={null} label="Total" value={campaign.total} color="blue" />
      </div>

      {/* Failed emails list */}
      {failedCount > 0 && (
        <div className="bg-red-50 border border-red-100 rounded-xl p-4 space-y-2">
          <h3 className="font-semibold text-red-700 text-sm">Failed Emails ({failedCount})</h3>
          <div className="space-y-1.5 max-h-48 overflow-y-auto">
            {campaign.recipients
              .filter(r => r.status === 'failed')
              .map(r => (
                <div key={r.row_index} className="flex items-start gap-2 text-xs">
                  <XCircle size={13} className="text-red-400 mt-0.5 shrink-0" />
                  <div>
                    <span className="font-mono text-red-700">{r.email}</span>
                    {r.error_message && (
                      <span className="text-red-400 ml-2">{r.error_message}</span>
                    )}
                  </div>
                </div>
              ))}
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex flex-wrap gap-3 justify-center">
        <button
          onClick={() => exportResults(campaign.campaign_id)}
          className="flex items-center gap-2 px-5 py-2.5 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 text-sm font-medium transition shadow-sm"
        >
          <Download size={15} /> Export CSV
        </button>
        {failedCount > 0 && (
          <button
            onClick={handleRetry}
            disabled={retrying}
            className="flex items-center gap-2 px-5 py-2.5 bg-amber-500 hover:bg-amber-600 text-white rounded-lg text-sm font-semibold transition shadow-sm disabled:opacity-60"
          >
            <RefreshCw size={15} className={retrying ? 'animate-spin' : ''} />
            Retry {failedCount} Failed
          </button>
        )}
        <button
          onClick={onNewCampaign}
          className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-semibold transition shadow-sm"
        >
          <PlusCircle size={15} /> New Campaign
        </button>
      </div>
    </div>
  );
};

const ResultStat: React.FC<{
  icon: React.ReactNode;
  label: string;
  value: number;
  color: string;
}> = ({ icon, label, value, color }) => {
  const colors: Record<string, string> = {
    green: 'border-green-200 bg-green-50 text-green-800',
    red: 'border-red-200 bg-red-50 text-red-800',
    gray: 'border-gray-200 bg-gray-50 text-gray-700',
    blue: 'border-blue-200 bg-blue-50 text-blue-800',
  };
  return (
    <div className={`border rounded-xl p-4 text-center ${colors[color]}`}>
      <div className="flex justify-center mb-1">{icon}</div>
      <div className="text-2xl font-bold">{value}</div>
      <div className="text-xs font-medium opacity-70 mt-0.5">{label}</div>
    </div>
  );
};
