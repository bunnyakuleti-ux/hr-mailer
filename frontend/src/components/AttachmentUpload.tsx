import React, { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Paperclip, X, FileText, Loader2 } from 'lucide-react';
import { uploadAttachment, deleteAttachment } from '../api';
import type { AttachmentInfo } from '../types';

interface AttachmentUploadProps {
  attachment: AttachmentInfo | null;
  onAttachmentChange: (a: AttachmentInfo | null) => void;
}

const fileIcon = (filename: string) => {
  const ext = filename.split('.').pop()?.toLowerCase();
  if (['pdf'].includes(ext || '')) return '📄';
  if (['doc', 'docx'].includes(ext || '')) return '📝';
  if (['png', 'jpg', 'jpeg'].includes(ext || '')) return '🖼️';
  return '📎';
};

export const AttachmentUpload: React.FC<AttachmentUploadProps> = ({
  attachment,
  onAttachmentChange,
}) => {
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const onDrop = useCallback(async (accepted: File[]) => {
    if (!accepted.length) return;
    setLoading(true);
    setError(null);
    try {
      // Remove old attachment if any
      if (attachment) {
        await deleteAttachment(attachment.attachment_id).catch(() => {});
        onAttachmentChange(null);
      }
      const info = await uploadAttachment(accepted[0]);
      onAttachmentChange(info);
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Failed to upload attachment.');
    } finally {
      setLoading(false);
    }
  }, [attachment, onAttachmentChange]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/msword': ['.doc'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'text/plain': ['.txt'],
      'image/png': ['.png'],
      'image/jpeg': ['.jpg', '.jpeg'],
    },
    maxFiles: 1,
    disabled: loading,
  });

  const handleRemove = async () => {
    if (!attachment) return;
    try {
      await deleteAttachment(attachment.attachment_id);
    } catch {}
    onAttachmentChange(null);
  };

  return (
    <div className="max-w-xl mx-auto py-6 px-4 space-y-5">
      <div>
        <h2 className="text-xl font-bold text-gray-900">Add Attachment</h2>
        <p className="text-sm text-gray-500 mt-1">
          Upload a resume or any document to attach to every email.
        </p>
      </div>

      {attachment ? (
        <div className="flex items-center gap-4 p-4 bg-green-50 border border-green-200 rounded-xl">
          <span className="text-3xl">{fileIcon(attachment.filename)}</span>
          <div className="flex-1 min-w-0">
            <p className="font-semibold text-gray-800 truncate">{attachment.filename}</p>
            <p className="text-xs text-gray-500 mt-0.5">{attachment.size_mb} MB</p>
          </div>
          <div className="flex gap-2">
            <div {...getRootProps()}>
              <input {...getInputProps()} />
              <button
                type="button"
                className="text-xs px-3 py-1.5 border border-gray-300 rounded-lg hover:bg-gray-50 text-gray-600 transition"
              >
                Replace
              </button>
            </div>
            <button
              onClick={handleRemove}
              className="p-1.5 text-red-500 hover:bg-red-50 rounded-lg transition"
              title="Remove attachment"
            >
              <X size={16} />
            </button>
          </div>
        </div>
      ) : (
        <div
          {...getRootProps()}
          className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition
            ${isDragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300 bg-gray-50 hover:border-blue-400 hover:bg-blue-50/30'}
            ${loading ? 'opacity-60 cursor-not-allowed' : ''}
          `}
        >
          <input {...getInputProps()} />
          {loading ? (
            <div className="flex flex-col items-center gap-2">
              <Loader2 size={32} className="animate-spin text-blue-500" />
              <p className="text-sm text-blue-600 font-medium">Uploading...</p>
            </div>
          ) : (
            <>
              <Paperclip size={36} className="mx-auto mb-3 text-gray-400" />
              <p className="font-semibold text-gray-700">Drag & drop your attachment here</p>
              <p className="text-xs text-gray-400 mt-1">PDF, DOC, DOCX, TXT, PNG, JPG — max 10 MB</p>
            </>
          )}
        </div>
      )}

      {error && (
        <div className="flex items-center gap-2 text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg p-3">
          <X size={14} className="shrink-0" />
          {error}
        </div>
      )}

      <div className="text-xs text-gray-400 flex items-center gap-1.5 p-3 bg-gray-50 rounded-lg border border-gray-100">
        <FileText size={13} />
        Attachment is optional. If no file is attached, emails will be sent without an attachment.
      </div>
    </div>
  );
};
