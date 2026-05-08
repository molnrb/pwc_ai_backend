import React, { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { ChevronLeft, ChevronRight, CheckCircle2 } from 'lucide-react';
import { StepUpload } from './StepUpload';
import { StepConfigure } from './StepConfigure';
import { StepReview } from './StepReview';

export interface PendingUploadFile {
  file: File;
  id: string;
  name: string;
  sizeLabel: string;
}

export const NewAudit = ({ onComplete }: { onComplete: (files: File[]) => Promise<void> | void }) => {
  const [step, setStep] = useState(1);
  const [files, setFiles] = useState<PendingUploadFile[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleNext = () => setStep(s => Math.min(3, s + 1));
  const handlePrev = () => setStep(s => Math.max(1, s - 1));

  const handleComplete = async () => {
    setSubmitting(true);
    setError(null);

    try {
      await onComplete(files.map((entry) => entry.file));
    } catch (err: any) {
      setError(err.message || 'Launch failed.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="p-8 overflow-y-auto custom-scrollbar flex-1 bg-[#1A1A2E] max-w-4xl mx-auto w-full">
      {/* Progress Stepper */}
      <div className="flex items-center justify-between mb-16 relative">
        <div className="absolute top-1/2 -translate-y-1/2 left-0 right-0 h-0.5 bg-[#3D3D4E] z-0" />
        {[1, 2, 3].map(i => (
          <div key={i} className={`relative z-10 w-10 h-10 rounded-full flex items-center justify-center font-bold transition-all border-2 ${
            step >= i ? 'bg-[#E8521A] border-[#E8521A] text-white shadow-[0_0_15px_rgba(232,82,26,0.3)]' : 'bg-[#1A1A2E] border-[#3D3D4E] text-slate-600'
          }`}>
            {step > i ? <CheckCircle2 className="w-6 h-6" /> : i}
          </div>
        ))}
      </div>

      <AnimatePresence mode="wait">
        <motion.div
           key={step}
           initial={{ opacity: 0, x: 20 }}
           animate={{ opacity: 1, x: 0 }}
           exit={{ opacity: 0, x: -20 }}
           transition={{ duration: 0.2 }}
        >
          {step === 1 && <StepUpload files={files} setFiles={setFiles} />}
          {step === 2 && <StepConfigure />}
          {step === 3 && <StepReview files={files} onComplete={handleComplete} submitting={submitting} error={error} />}
        </motion.div>
      </AnimatePresence>

      <div className="mt-12 flex justify-between">
        {step > 1 && (
          <button onClick={handlePrev} className="flex items-center gap-2 text-slate-500 hover:text-white transition-colors uppercase font-bold text-xs tracking-widest">
            <ChevronLeft className="w-4 h-4" /> Back
          </button>
        )}
        {step < 3 && (
          <button onClick={handleNext} className="ml-auto flex items-center gap-2 text-[#E8521A] hover:text-white transition-colors uppercase font-bold text-xs tracking-widest">
            Next <ChevronRight className="w-4 h-4" />
          </button>
        )}
      </div>
    </div>
  );
};
