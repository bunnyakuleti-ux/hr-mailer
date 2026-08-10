import React from 'react';
import { Check } from 'lucide-react';
import type { Step } from '../types';

const STEPS: { key: Step; label: string }[] = [
  { key: 'gmail', label: 'Gmail' },
  { key: 'contacts', label: 'Contacts' },
  { key: 'compose', label: 'Compose' },
  { key: 'attachment', label: 'Attachment' },
  { key: 'preview', label: 'Preview' },
  { key: 'send', label: 'Send' },
  { key: 'results', label: 'Results' },
];

interface StepperProps {
  currentStep: Step;
  onStepClick?: (step: Step) => void;
}

const stepIndex = (step: Step) => STEPS.findIndex(s => s.key === step);

export const Stepper: React.FC<StepperProps> = ({ currentStep, onStepClick }) => {
  const current = stepIndex(currentStep);

  return (
    <div className="w-full bg-white border-b border-gray-200 px-6 py-4">
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center justify-between relative">
          {/* connector line */}
          <div className="absolute top-4 left-0 right-0 h-0.5 bg-gray-200 z-0" />
          <div
            className="absolute top-4 left-0 h-0.5 bg-blue-600 z-0 transition-all duration-500"
            style={{ width: `${(current / (STEPS.length - 1)) * 100}%` }}
          />

          {STEPS.map((step, idx) => {
            const isDone = idx < current;
            const isActive = idx === current;
            const isClickable = idx < current && onStepClick;

            return (
              <div key={step.key} className="flex flex-col items-center z-10">
                <button
                  onClick={() => isClickable && onStepClick(step.key)}
                  disabled={!isClickable}
                  className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold border-2 transition-all
                    ${isDone ? 'bg-blue-600 border-blue-600 text-white cursor-pointer hover:bg-blue-700' : ''}
                    ${isActive ? 'bg-white border-blue-600 text-blue-600' : ''}
                    ${!isDone && !isActive ? 'bg-white border-gray-300 text-gray-400 cursor-default' : ''}
                  `}
                >
                  {isDone ? <Check size={14} /> : idx + 1}
                </button>
                <span
                  className={`mt-1.5 text-xs font-medium hidden sm:block
                    ${isActive ? 'text-blue-600' : isDone ? 'text-blue-500' : 'text-gray-400'}
                  `}
                >
                  {step.label}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
