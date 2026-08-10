import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, FileSpreadsheet, XCircle, AlertCircle, Users, ChevronDown } from 'lucide-react';
import { uploadContacts } from '../api';
import type { ParsedContacts, Recipient } from '../types';

interface ContactsUploadProps {
  onContactsParsed: (data: ParsedContacts) => void;
  parsed?: ParsedContacts;
}

const StatusBadge: React.FC<{ r: Recipient }> = ({ r }) => {
  if (!r.is_valid && r.is_duplicate)
    return <span className="text-xs px-2 py-0.5 rounded-full bg-yellow-100 text-yellow-700">Duplicate</span>;
  if (!r.is_valid)
    return <span className="text-xs px-2 py-0.5 rounded-full bg-red-100 text-red-700">Invalid</span>;
  return <span className="text-xs px-2 py-0.5 rounded-full bg-green-100 text-green-700">Valid</span>;
};

export const ContactsUpload: React.FC<ContactsUploadProps> = ({ onContactsParsed, parsed }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [selectedEmailCol, setSelectedEmailCol] = useState<string>('');
  const [showAll, setShowAll] = useState(false);

  const processFile = useCallback(async (f: File, emailCol?: string) => {
    setLoading(true);
    setError(null);
    try {
      const result = await uploadContacts(f, emailCol);
      onContactsParsed(result);
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Failed to parse file. Please check format.');
    } finally {
      setLoading(false);
    }
  }, [onContactsParsed]);

  const onDrop = useCallback((accepted: File[]) => {
    if (!accepted.length) return;
    const f = accepted[0];
    setFile(f);
    setSelectedEmailCol('');
    processFile(f);
  }, [processFile]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/csv': ['.csv'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls'],
    },
    maxFiles: 1,
    disabled: loading,
  });

  const handleColumnChange = (col: string) => {
    setSelectedEmailCol(col);
    if (file) processFile(file, col);
  };

  const displayedRecipients = showAll ? parsed?.recipients : parsed?.recipients.slice(0, 10);

  return (
    <div className="max-w-3xl mx-auto py-6 px-4 space-y-6">
      <div>
        <h2 className="text-xl font-bold text-gray-900">Upload HR Contact File</h2>
        <p className="text-sm text-gray-500 mt-1">Upload an Excel or CSV file containing recruiter/HR email addresses.</p>
      </div>

      {/* Dropzone */}
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition
          ${isDragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300 bg-gray-50 hover:border-blue-400 hover:bg-blue-50/40'}
          ${loading ? 'opacity-60 cursor-not-allowed' : ''}
        `}
      >
        <input {...getInputProps()} />
        <Upload size={36} className={`mx-auto mb-3 ${isDragActive ? 'text-blue-500' : 'text-gray-400'}`} />
        {loading ? (
          <p className="text-blue-600 font-medium animate-pulse">Parsing file...</p>
        ) : isDragActive ? (
          <p className="text-blue-600 font-medium">Drop your file here</p>
        ) : (
          <>
            <p className="font-semibold text-gray-700">Drag & drop your file here, or click to browse</p>
            <p className="text-xs text-gray-400 mt-1">Supports .xlsx, .xls, .csv</p>
          </>
        )}
        {file && !loading && (
          <div className="mt-2 inline-flex items-center gap-2 text-xs text-gray-600 bg-white border rounded-lg px-3 py-1">
            <FileSpreadsheet size={14} className="text-green-600" />
            {file.name}
          </div>
        )}
      </div>

      {error && (
        <div className="flex items-start gap-2 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
          <XCircle size={16} className="mt-0.5 shrink-0" />
          {error}
        </div>
      )}

      {/* Column selector if ambiguous */}
      {parsed && parsed.columns.length > 1 && (
        <div className="flex items-center gap-3 p-3 bg-blue-50 border border-blue-100 rounded-lg">
          <AlertCircle size={16} className="text-blue-500 shrink-0" />
          <div className="flex-1 text-sm text-blue-800">
            <span className="font-medium">Select the email column:</span>{' '}
            <span className="text-blue-600">(auto-detected: {parsed.detected_email_column})</span>
          </div>
          <select
            value={selectedEmailCol || parsed.detected_email_column || ''}
            onChange={e => handleColumnChange(e.target.value)}
            className="text-sm border border-blue-200 rounded-lg px-2 py-1 bg-white focus:outline-none focus:ring-2 focus:ring-blue-300"
          >
            {parsed.columns.map(col => (
              <option key={col} value={col}>{col}</option>
            ))}
          </select>
        </div>
      )}

      {/* Stats */}
      {parsed && (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <StatCard label="Total Rows" value={parsed.total_rows} color="gray" />
            <StatCard label="Valid Emails" value={parsed.valid_count} color="green" />
            <StatCard label="Invalid" value={parsed.invalid_count} color="red" />
            <StatCard label="Duplicates Removed" value={parsed.duplicate_count} color="yellow" />
          </div>

          {/* Recipient table */}
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <div className="px-4 py-3 border-b border-gray-100 flex items-center gap-2">
              <Users size={16} className="text-gray-500" />
              <span className="font-semibold text-gray-700 text-sm">Recipient Preview</span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-50 text-gray-500 text-xs uppercase tracking-wide">
                    <th className="px-4 py-2 text-left w-8">#</th>
                    <th className="px-4 py-2 text-left">Name</th>
                    <th className="px-4 py-2 text-left">Email</th>
                    <th className="px-4 py-2 text-left">Company</th>
                    <th className="px-4 py-2 text-left">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {displayedRecipients?.map((r, i) => (
                    <tr key={r.row_index} className={`border-t border-gray-50 ${!r.is_valid ? 'bg-red-50/30' : ''}`}>
                      <td className="px-4 py-2 text-gray-400">{i + 1}</td>
                      <td className="px-4 py-2 text-gray-700">{r.name || <span className="text-gray-300">—</span>}</td>
                      <td className="px-4 py-2 font-mono text-gray-800">{r.email || <span className="text-gray-300">—</span>}</td>
                      <td className="px-4 py-2 text-gray-700">{r.company || <span className="text-gray-300">—</span>}</td>
                      <td className="px-4 py-2"><StatusBadge r={r} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {(parsed.recipients.length > 10) && (
              <button
                onClick={() => setShowAll(!showAll)}
                className="w-full py-2.5 text-xs text-blue-600 hover:bg-blue-50 flex items-center justify-center gap-1 border-t border-gray-100"
              >
                <ChevronDown size={14} className={showAll ? 'rotate-180' : ''} />
                {showAll ? 'Show less' : `Show all ${parsed.recipients.length} rows`}
              </button>
            )}
          </div>
        </>
      )}
    </div>
  );
};

const StatCard: React.FC<{ label: string; value: number; color: 'gray' | 'green' | 'red' | 'yellow' }> = ({ label, value, color }) => {
  const colors = {
    gray: 'bg-gray-50 border-gray-200 text-gray-800',
    green: 'bg-green-50 border-green-200 text-green-800',
    red: 'bg-red-50 border-red-200 text-red-800',
    yellow: 'bg-yellow-50 border-yellow-200 text-yellow-800',
  };
  return (
    <div className={`border rounded-xl p-4 text-center ${colors[color]}`}>
      <div className="text-2xl font-bold">{value}</div>
      <div className="text-xs mt-0.5 font-medium opacity-70">{label}</div>
    </div>
  );
};
