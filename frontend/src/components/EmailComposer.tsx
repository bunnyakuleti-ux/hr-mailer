import React from 'react';
import { Info } from 'lucide-react';

interface EmailComposerProps {
  subject: string;
  body: string;
  onSubjectChange: (v: string) => void;
  onBodyChange: (v: string) => void;
}

const VARIABLES = [
  { label: '{{name}}', desc: "Recipient's name" },
  { label: '{{company}}', desc: 'Company name' },
  { label: '{{email}}', desc: "Recipient's email" },
];

export const EmailComposer: React.FC<EmailComposerProps> = ({
  subject, body, onSubjectChange, onBodyChange,
}) => {
  const insertVariable = (variable: string) => {
    onBodyChange(body + variable);
  };

  return (
    <div className="max-w-3xl mx-auto py-6 px-4 space-y-5">
      <div>
        <h2 className="text-xl font-bold text-gray-900">Compose Email</h2>
        <p className="text-sm text-gray-500 mt-1">
          Write a common email. Use variables for personalization.
        </p>
      </div>

      {/* Variable chips */}
      <div className="flex items-start gap-3 p-3 bg-blue-50 border border-blue-100 rounded-lg">
        <Info size={15} className="text-blue-500 mt-0.5 shrink-0" />
        <div>
          <p className="text-xs font-semibold text-blue-700 mb-1.5">Available personalization variables:</p>
          <div className="flex flex-wrap gap-2">
            {VARIABLES.map(v => (
              <button
                key={v.label}
                onClick={() => insertVariable(v.label)}
                title={`Insert ${v.label} — ${v.desc}`}
                className="inline-flex items-center gap-1 px-2.5 py-1 bg-white border border-blue-200 text-blue-700 rounded-md text-xs font-mono hover:bg-blue-100 transition"
              >
                {v.label}
                <span className="text-blue-400 font-sans font-normal">({v.desc})</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Subject */}
      <div className="space-y-1.5">
        <label className="block text-sm font-semibold text-gray-700">
          Subject <span className="text-red-500">*</span>
        </label>
        <input
          type="text"
          value={subject}
          onChange={e => onSubjectChange(e.target.value)}
          placeholder="e.g. Application for Software Developer Role"
          className="w-full border border-gray-300 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 focus:border-transparent transition"
        />
      </div>

      {/* Body */}
      <div className="space-y-1.5">
        <label className="block text-sm font-semibold text-gray-700">
          Email Body <span className="text-red-500">*</span>
        </label>
        <textarea
          value={body}
          onChange={e => onBodyChange(e.target.value)}
          rows={12}
          placeholder={`Dear {{name}},\n\nI am applying for a software developer position at {{company}}.\n\nPlease find my resume attached.\n\nThank you,\nYour Name`}
          className="w-full border border-gray-300 rounded-lg px-4 py-3 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-400 focus:border-transparent resize-y transition"
        />
        <div className="flex justify-between text-xs text-gray-400">
          <span>Click a variable above to insert it at the cursor</span>
          <span>{body.length} characters</span>
        </div>
      </div>
    </div>
  );
};
