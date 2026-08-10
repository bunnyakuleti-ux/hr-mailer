import { useState, useEffect } from 'react';
import { Toaster, toast } from 'react-hot-toast';
import { Mail, ChevronRight, ChevronLeft, AlertCircle } from 'lucide-react';
import { saveSession } from './api';

import { Stepper } from './components/Stepper';
import { GmailConnect } from './components/GmailConnect';
import { ContactsUpload } from './components/ContactsUpload';
import { EmailComposer } from './components/EmailComposer';
import { AttachmentUpload } from './components/AttachmentUpload';
import { EmailPreview } from './components/EmailPreview';
import { SendConfirm } from './components/SendConfirm';
import { SendingProgress } from './components/SendingProgress';
import { Results } from './components/Results';

import { sendCampaign, getAuthStatus } from './api';
import type { Step, AuthStatus, ParsedContacts, AttachmentInfo, CampaignStatus } from './types';

const STEP_ORDER: Step[] = ['gmail', 'contacts', 'compose', 'attachment', 'preview', 'send', 'results'];

export default function App() {
  const [step, setStep] = useState<Step>('gmail');
  const [auth, setAuth] = useState<AuthStatus>({ connected: false });

  // Data state
  const [parsedContacts, setParsedContacts] = useState<ParsedContacts | null>(null);
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const [attachment, setAttachment] = useState<AttachmentInfo | null>(null);
  const [campaignId, setCampaignId] = useState<string | null>(null);
  const [completedCampaign, setCompletedCampaign] = useState<CampaignStatus | null>(null);
  const [delaySeconds, setDelaySeconds] = useState(2);
  const [sending, setSending] = useState(false);

  // Check auth on mount (handles redirect back from Google)
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const session = params.get('session');
    if (session) {
      saveSession(session);
      window.history.replaceState({}, '', window.location.pathname);
    }
    if (params.get('auth_error')) {
      window.history.replaceState({}, '', window.location.pathname);
      toast.error('Gmail connection failed. Please try again.');
    }

    getAuthStatus().then(s => {
      setAuth(s);
      if (s.connected) setStep('contacts');
    }).catch(() => {});
  }, []);

  const goNext = () => {
    const idx = STEP_ORDER.indexOf(step);
    if (idx < STEP_ORDER.length - 1) setStep(STEP_ORDER[idx + 1]);
  };

  const goBack = () => {
    const idx = STEP_ORDER.indexOf(step);
    if (idx > 0) setStep(STEP_ORDER[idx - 1]);
  };

  const canGoNext = (): boolean => {
    switch (step) {
      case 'gmail': return auth.connected;
      case 'contacts': return !!parsedContacts && parsedContacts.valid_count > 0;
      case 'compose': return subject.trim().length > 0 && body.trim().length > 0;
      case 'attachment': return true; // optional
      case 'preview': return true;
      case 'send': return false; // handled by SendConfirm
      default: return false;
    }
  };

  const handleSend = async () => {
    if (!parsedContacts) return;
    const validRecipients = parsedContacts.recipients.filter(r => r.is_valid && !r.is_duplicate);
    setSending(true);
    try {
      const result = await sendCampaign({
        subject,
        body,
        recipients: validRecipients,
        attachment_id: attachment?.attachment_id,
        delay_seconds: delaySeconds,
      });
      setCampaignId(result.campaign_id);
      setStep('results'); // goes to progress view
      toast.success(`Campaign started! Sending ${result.total} emails…`);
    } catch (e: any) {
      toast.error(e.response?.data?.detail || 'Failed to start campaign.');
    } finally {
      setSending(false);
    }
  };

  const handleCampaignComplete = (status: CampaignStatus) => {
    setCompletedCampaign(status);
    toast.success(`Done! Sent: ${status.sent}, Failed: ${status.failed}`);
  };

  const handleRetry = (newCampaignId: string) => {
    setCampaignId(newCampaignId);
    setCompletedCampaign(null);
  };

  const handleNewCampaign = () => {
    setParsedContacts(null);
    setSubject('');
    setBody('');
    setAttachment(null);
    setCampaignId(null);
    setCompletedCampaign(null);
    setSending(false);
    setStep('contacts');
  };

  const renderStep = () => {
    switch (step) {
      case 'gmail':
        return <GmailConnect onConnected={(s) => { setAuth(s); if (s.connected) setStep('contacts'); }} />;

      case 'contacts':
        return (
          <ContactsUpload
            onContactsParsed={setParsedContacts}
            parsed={parsedContacts || undefined}
          />
        );

      case 'compose':
        return (
          <EmailComposer
            subject={subject}
            body={body}
            onSubjectChange={setSubject}
            onBodyChange={setBody}
          />
        );

      case 'attachment':
        return (
          <AttachmentUpload
            attachment={attachment}
            onAttachmentChange={setAttachment}
          />
        );

      case 'preview':
        return (
          <EmailPreview
            subject={subject}
            body={body}
            recipients={parsedContacts?.recipients || []}
            attachment={attachment}
            fromEmail={auth.email || ''}
          />
        );

      case 'send':
        return (
          <SendConfirm
            recipients={parsedContacts?.recipients || []}
            subject={subject}
            attachment={attachment}
            delaySeconds={delaySeconds}
            onDelayChange={setDelaySeconds}
            onConfirm={handleSend}
            onCancel={goBack}
            sending={sending}
          />
        );

      case 'results':
        if (completedCampaign) {
          return (
            <Results
              campaign={completedCampaign}
              onRetry={handleRetry}
              onNewCampaign={handleNewCampaign}
            />
          );
        }
        if (campaignId) {
          return (
            <SendingProgress
              campaignId={campaignId}
              onComplete={handleCampaignComplete}
            />
          );
        }
        return <div className="py-10 text-center text-gray-400">No campaign running.</div>;

      default:
        return null;
    }
  };

  const showNav = !['gmail', 'send', 'results'].includes(step);

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <Toaster position="top-right" />

      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-4 shadow-sm">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-blue-600 rounded-xl flex items-center justify-center shadow-sm">
              <Mail size={18} className="text-white" />
            </div>
            <div>
              <h1 className="font-bold text-gray-900 text-lg leading-tight">HR Mailer</h1>
              <p className="text-xs text-gray-400 leading-tight hidden sm:block">
                Send personalized job application emails with attachments
              </p>
            </div>
          </div>
          {auth.connected && (
            <div className="flex items-center gap-2 text-xs text-green-700 bg-green-50 border border-green-200 px-3 py-1.5 rounded-full">
              <span className="w-2 h-2 bg-green-500 rounded-full" />
              {auth.email}
            </div>
          )}
        </div>
      </header>

      {/* Stepper */}
      <Stepper
        currentStep={step}
        onStepClick={(s) => {
          // Allow going back to any completed step
          const current = STEP_ORDER.indexOf(step);
          const target = STEP_ORDER.indexOf(s);
          if (target < current) setStep(s);
        }}
      />

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <div className="max-w-4xl mx-auto px-4">
          {renderStep()}
        </div>
      </main>

      {/* Bottom nav */}
      {showNav && (
        <footer className="bg-white border-t border-gray-200 px-6 py-4">
          <div className="max-w-4xl mx-auto flex items-center justify-between">
            <button
              onClick={goBack}
              disabled={STEP_ORDER.indexOf(step) === 0}
              className="flex items-center gap-2 px-4 py-2 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-40 transition"
            >
              <ChevronLeft size={16} /> Back
            </button>

            {/* Validation hint */}
            {!canGoNext() && (
              <div className="flex items-center gap-1.5 text-xs text-amber-600">
                <AlertCircle size={13} />
                {step === 'contacts' && 'Upload a file with valid emails to continue'}
                {step === 'compose' && 'Subject and body are required'}
              </div>
            )}

            <button
              onClick={goNext}
              disabled={!canGoNext()}
              className="flex items-center gap-2 px-5 py-2 text-sm bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg disabled:opacity-40 disabled:cursor-not-allowed transition shadow-sm"
            >
              {step === 'preview' ? 'Proceed to Send' : 'Next'}
              <ChevronRight size={16} />
            </button>
          </div>
        </footer>
      )}
    </div>
  );
}
